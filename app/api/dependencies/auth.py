from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.core.user_mapper import to_public_user_document
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserResponse

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    user_id = decode_access_token(token)
    if not user_id:
        raise UnauthorizedError("Invalid or expired token")

    repository = UserRepository()
    user = repository.get_by_id(user_id)
    if not user:
        raise UnauthorizedError("Invalid token user")

    clean_user = to_public_user_document(user)
    return UserResponse(**clean_user)
