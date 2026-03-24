from fastapi import Depends

from app.api.dependencies.auth import get_current_user
from app.core.exceptions import ForbiddenError
from app.schemas.user import UserResponse


def get_current_provider(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    if current_user.role != "provider":
        raise ForbiddenError("Only provider users can access this resource")
    return current_user
