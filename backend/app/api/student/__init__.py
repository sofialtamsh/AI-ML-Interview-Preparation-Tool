from fastapi import APIRouter, Depends

from app.api.student import account, auth, learn, practice, progress
from app.auth.deps import require_csrf_header

router = APIRouter(dependencies=[Depends(require_csrf_header)])
router.include_router(auth.router)
router.include_router(account.router)
router.include_router(learn.router)
router.include_router(practice.router)
router.include_router(progress.router)
