from fastapi import APIRouter, Depends

from app.api.admin import (
    agents,
    ai_usage,
    analytics,
    audit,
    auth,
    content,
    content_quality,
    intelligence,
    overview,
    practice,
    research,
    sources,
    students,
    taxonomy,
    team,
)
from app.auth.deps import require_csrf_header

router = APIRouter(dependencies=[Depends(require_csrf_header)])
router.include_router(auth.router)
router.include_router(overview.router)
router.include_router(students.router)
router.include_router(team.router)
router.include_router(audit.router)
router.include_router(ai_usage.router)
router.include_router(sources.router)
router.include_router(agents.router)
router.include_router(intelligence.router)
router.include_router(research.router)
router.include_router(content.router)
router.include_router(content_quality.router)
router.include_router(taxonomy.router)
router.include_router(practice.router)
router.include_router(analytics.router)
