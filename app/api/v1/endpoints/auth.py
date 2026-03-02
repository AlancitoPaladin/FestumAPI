from fastapi import APIRouter, Depends, status

from app.api.dependencies.auth import get_current_user
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest, service: AuthService = Depends(AuthService)
) -> TokenResponse:
    return service.register(payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, service: AuthService = Depends(AuthService)) -> TokenResponse:
    return service.login(payload)


@router.get("/me", response_model=UserResponse)
def me(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    return current_user

