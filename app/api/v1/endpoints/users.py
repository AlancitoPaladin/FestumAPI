from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies.auth import get_current_user
from app.schemas.user import UserListResponse, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    service: UserService = Depends(UserService),
    _: UserResponse = Depends(get_current_user),
) -> UserResponse:
    return service.get(user_id)


@router.get("", response_model=UserListResponse)
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: UserService = Depends(UserService),
    _: UserResponse = Depends(get_current_user),
) -> UserListResponse:
    return service.list(page=page, page_size=page_size)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    payload: UserUpdate,
    service: UserService = Depends(UserService),
    _: UserResponse = Depends(get_current_user),
) -> UserResponse:
    return service.update(user_id=user_id, user_data=payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    service: UserService = Depends(UserService),
    _: UserResponse = Depends(get_current_user),
) -> None:
    service.delete(user_id)
