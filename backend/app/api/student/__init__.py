from fastapi import APIRouter, Depends

from app.api.student import account, auth
from app.auth.deps import require_csrf_header

router = APIRouter(dependencies=[Depends(require_csrf_header)])
router.include_router(auth.router)
router.include_router(account.router)
