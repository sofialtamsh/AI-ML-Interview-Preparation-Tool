"""Platform analytics for admins: engagement, completion, quiz and practice performance, weak
topics and cohorts, with filters, and a CSV export of every student's learning (audited)."""

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.deps import AdminContext, require_permission
from app.auth.permissions import Perm
from app.core.audit import record_audit
from app.core.db import get_db
from app.core.security import utcnow
from app.models import Student
from app.progress.analytics import analytics_report, students_csv
from app.progress.service import local_tz
from app.schemas.progress import AnalyticsReport

router = APIRouter(prefix="/analytics", tags=["admin-analytics"])

MAX_RANGE_DAYS = 366


@router.get("", response_model=AnalyticsReport)
def analytics(
    start: date | None = None,
    end: date | None = None,
    cohort_id: uuid.UUID | None = None,
    domain: str | None = Query(default=None, max_length=200),
    topic: str | None = Query(default=None, max_length=300),
    student_id: uuid.UUID | None = None,
    ctx: AdminContext = Depends(require_permission(Perm.ANALYTICS_VIEW)),
    db: Session = Depends(get_db),
) -> AnalyticsReport:
    """Filtering to one student shows their data, so it also needs students.view."""
    student = None
    if student_id:
        if Perm.STUDENTS_VIEW not in ctx.permissions:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "You need access to student profiles for this filter."
            )
        student = db.get(Student, student_id)
        if student is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Student not found.")
    today = utcnow().astimezone(local_tz()).date()
    end = end or today
    start = start or end - timedelta(days=29)
    if start > end or (end - start).days > MAX_RANGE_DAYS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose a range of up to a year, start first."
        )
    return AnalyticsReport.model_validate(
        analytics_report(
            db,
            start=start,
            end=end,
            cohort_id=cohort_id,
            domain=domain,
            topic=topic,
            student=student,
        )
    )


@router.get("/students.csv")
def export_students(
    request: Request,
    cohort_id: uuid.UUID | None = None,
    ctx: AdminContext = Depends(require_permission(Perm.ANALYTICS_EXPORT)),
    db: Session = Depends(get_db),
) -> Response:
    """Every student's learning summary as CSV. Contains personal data, so it is audited."""
    content = students_csv(db, cohort_id)
    record_audit(
        db,
        request,
        ctx,
        "analytics.students_exported",
        "students",
        None,
        {"cohort_id": str(cohort_id) if cohort_id else None, "rows": content.count("\n") - 1},
    )
    db.commit()
    stamp = utcnow().astimezone(local_tz()).strftime("%Y-%m-%d")
    return Response(
        content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="students-{stamp}.csv"'},
    )
