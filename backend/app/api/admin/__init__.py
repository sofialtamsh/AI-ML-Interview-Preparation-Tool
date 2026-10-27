from fastapi import APIRouter, Depends

from app.api.admin import ai_usage, audit, auth, overview, students, team
from app.auth.deps import require_csrf_header

router = APIRouter(dependencies=[Depends(require_csrf_header)])
router.include_router(auth.router)
router.include_router(overview.router)
router.include_router(students.router)
router.include_router(team.router)
router.include_router(audit.router)
router.include_router(ai_usage.router)
