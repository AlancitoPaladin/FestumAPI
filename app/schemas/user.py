from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class UserBase(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=40)
    last_name: str = Field(..., min_length=2, max_length=40)
    email: EmailStr
    phone: str | None = Field(default=None, pattern=r"^\+?[1-9]\d{7,14}$")
    birth_date: date | None = None
    is_active: bool = True

    @field_validator("first_name", "last_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        cleaned_value = " ".join(value.split())
        if not cleaned_value.replace(" ", "").isalpha():
            raise ValueError("Only letters are allowed in names")
        return cleaned_value.title()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class UserUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=2, max_length=40)
    last_name: str | None = Field(default=None, min_length=2, max_length=40)
    phone: str | None = Field(default=None, pattern=r"^\+?[1-9]\d{7,14}$")
    birth_date: date | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned_value = " ".join(value.split())
        if not cleaned_value.replace(" ", "").isalpha():
            raise ValueError("Only letters are allowed in names")
        return cleaned_value.title()

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "UserUpdate":
        if (
            self.first_name is None
            and self.last_name is None
            and self.phone is None
            and self.birth_date is None
        ):
            raise ValueError("At least one field is required for update")
        return self


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    items: list[UserResponse]
    page: int
    page_size: int
    total: int
