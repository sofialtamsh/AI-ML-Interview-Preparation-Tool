import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.deps import AdminContext, require_permission
from app.auth.permissions import Perm
from app.auth.sessions import revoke_sessions
from app.core.audit import record_audit
from app.core.db import get_db
from app.core.security import utcnow
from app.models import AuthSession, Cohort, LoginEvent, Student, StudentStatus
from app.schemas.admin import (
    CohortCreate,
    CohortWithCount,
    LoginEventOut,
    StudentDetail,
    StudentListItem,
    StudentUpdate,
)
from app.schemas.common import Page

router = APIRouter(tags=["admin-students"])

can_view = require_permission(Perm.STUDENTS_VIEW)
can_manage = require_permission(Perm.STUDENTS_MANAGE)


def _get_student(db: Session, student_id: uuid.UUID) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found.")
    return student


def _detail(db: Session, student: Student) -> StudentDetail:
    now = utcnow()
    active_sessions = db.scalar(
        select(func.count()).where(
            AuthSession.student_id == student.id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
    )
    logins = db.scalars(
        select(LoginEvent)
        .where(LoginEvent.student_id == student.id)
        .order_by(LoginEvent.created_at.desc())
        .limit(10)
    ).all()
    return StudentDetail(
        **StudentListItem.of(student).model_dump(),
        locked_until=student.locked_until
        if student.locked_until and student.locked_until > now
        else None,
        active_sessions=active_sessions or 0,
        recent_logins=[LoginEventOut.model_validate(e) for e in logins],
    )


@router.get("/students", response_model=Page[StudentListItem], dependencies=[Depends(can_view)])
def list_students(
    q: str | None = Query(default=None, max_length=200),
    status_filter: StudentStatus | None = Query(default=None, alias="status"),
    cohort_id: uuid.UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Page[StudentListItem]:
    conditions = []
    if q and q.strip():
        term = q.strip()
        pattern = f"%{term}%"
        matches = [Student.full_name.ilike(pattern), Student.email.ilike(pattern)]
        digits = term.upper().removeprefix("STU-")
        if digits.isdigit():
            matches.append(Student.student_number == int(digits))
        conditions.append(or_(*matches))
    if status_filter is not None:
        conditions.append(Student.status == status_filter)
    if cohort_id is not None:
        conditions.append(Student.cohort_id == cohort_id)

    total = db.scalar(select(func.count()).select_from(Student).where(*conditions)) or 0
    students = db.scalars(
        select(Student)
        .where(*conditions)
        .order_by(Student.created_at.desc(), Student.student_number.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[StudentListItem.of(s) for s in students],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/students/{student_id}", response_model=StudentDetail, dependencies=[Depends(can_view)]
)
def get_student(student_id: uuid.UUID, db: Session = Depends(get_db)) -> StudentDetail:
    return _detail(db, _get_student(db, student_id))


@router.patch("/students/{student_id}", response_model=StudentDetail)
def update_student(
    student_id: uuid.UUID,
    body: StudentUpdate,
    request: Request,
    ctx: AdminContext = Depends(can_manage),
    db: Session = Depends(get_db),
) -> StudentDetail:
    student = _get_student(db, student_id)
    changes: dict[str, dict[str, str | None]] = {}

    if body.status is not None and body.status != student.status:
        changes["status"] = {"from": student.status.value, "to": body.status.value}
        student.status = body.status
        if body.status is not StudentStatus.ACTIVE:
            # Suspension takes effect immediately on every device.
            revoke_sessions(db, student_id=student.id)

    if "cohort_id" in body.model_fields_set and body.cohort_id != student.cohort_id:
        if body.cohort_id is not None and db.get(Cohort, body.cohort_id) is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Cohort not found.")
        changes["cohort_id"] = {
            "from": str(student.cohort_id) if student.cohort_id else None,
            "to": str(body.cohort_id) if body.cohort_id else None,
        }
        student.cohort_id = body.cohort_id

    if changes:
        record_audit(db, request, ctx, "student.updated", "student", student.id, changes)
        db.commit()
        db.refresh(student)
    return _detail(db, student)


@router.get("/cohorts", response_model=list[CohortWithCount], dependencies=[Depends(can_view)])
def list_cohorts(db: Session = Depends(get_db)) -> list[CohortWithCount]:
    rows = db.execute(
        select(Cohort, func.count(Student.id))
        .outerjoin(Student, Student.cohort_id == Cohort.id)
        .group_by(Cohort.id)
        .order_by(Cohort.name)
    ).all()
    return [
        CohortWithCount(id=c.id, name=c.name, description=c.description, student_count=n)
        for c, n in rows
    ]


@router.post("/cohorts", response_model=CohortWithCount, status_code=status.HTTP_201_CREATED)
def create_cohort(
    body: CohortCreate,
    request: Request,
    ctx: AdminContext = Depends(can_manage),
    db: Session = Depends(get_db),
) -> CohortWithCount:
    cohort = Cohort(name=body.name, description=body.description)
    db.add(cohort)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "A cohort with this name already exists."
        ) from None
    record_audit(db, request, ctx, "cohort.created", "cohort", cohort.id, {"name": cohort.name})
    db.commit()
    return CohortWithCount(
        id=cohort.id, name=cohort.name, description=cohort.description, student_count=0
    )
