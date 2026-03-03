from app.core.exceptions import ResourceConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.core.user_mapper import to_public_user_document
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse


class AuthService:
    def __init__(self) -> None:
        self.repository = UserRepository()

    def register(self, payload: RegisterRequest) -> TokenResponse:
        existing_user = self.repository.get_by_email(str(payload.email))
        if existing_user:
            raise ResourceConflictError("A user with this email already exists")

        user_data = {
            "first_name": payload.first_name,
            "last_name": payload.last_name,
            "email": str(payload.email),
            "role": payload.role,
            "password_hash": hash_password(payload.password),
            "is_active": True,
            "phone": None,
            "birth_date": None,
        }
        created_user = self.repository.create(user_data)
        token, expires_in = create_access_token(created_user["id"])
        safe_user = self._public_user(created_user)
        return TokenResponse(access_token=token, expires_in=expires_in, user=safe_user)

    def login(self, payload: LoginRequest) -> TokenResponse:
        user = self.repository.get_by_email(str(payload.email))
        if not user or not user.get("password_hash"):
            raise UnauthorizedError("Invalid email or password")

        if not verify_password(payload.password, user["password_hash"]):
            raise UnauthorizedError("Invalid email or password")

        token, expires_in = create_access_token(user["id"])
        safe_user = self._public_user(user)
        return TokenResponse(access_token=token, expires_in=expires_in, user=safe_user)

    @staticmethod
    def _public_user(user_data: dict) -> UserResponse:
        clean_user = to_public_user_document(user_data)
        return UserResponse(**clean_user)
