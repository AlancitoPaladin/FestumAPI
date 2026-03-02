from app.core.exceptions import ResourceNotFoundError
from app.core.user_mapper import to_public_user_document
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserListResponse, UserResponse, UserUpdate


class UserService:
    def __init__(self) -> None:
        self.repository = UserRepository()

    def get(self, user_id: str) -> UserResponse:
        user = self.repository.get_by_id(user_id)
        if not user:
            raise ResourceNotFoundError("User not found")
        clean_user = to_public_user_document(user)
        return UserResponse(**clean_user)

    def list(self, page: int, page_size: int) -> UserListResponse:
        items, total = self.repository.list(page=page, page_size=page_size)
        return UserListResponse(
            items=[
                UserResponse(**to_public_user_document(item))
                for item in items
            ],
            page=page,
            page_size=page_size,
            total=total,
        )

    def update(self, user_id: str, user_data: UserUpdate) -> UserResponse:
        updated = self.repository.update(user_id, user_data.model_dump(exclude_none=True))
        if not updated:
            raise ResourceNotFoundError("User not found")
        clean_user = to_public_user_document(updated)
        return UserResponse(**clean_user)

    def delete(self, user_id: str) -> None:
        deleted = self.repository.delete(user_id)
        if not deleted:
            raise ResourceNotFoundError("User not found")
