from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, StringConstraints

from app.core.security import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page[T](ApiModel):
    items: list[T]
    total: int
    page: int
    page_size: int


NormalizedEmail = Annotated[EmailStr, AfterValidator(lambda v: v.strip().lower())]

NewPassword = Annotated[
    str, StringConstraints(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
]
# Existing passwords are only length-capped, so a policy change never locks anyone out.
AnyPassword = Annotated[str, StringConstraints(min_length=1, max_length=PASSWORD_MAX_LENGTH)]

PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)]


class LoginRequest(ApiModel):
    email: NormalizedEmail
    password: AnyPassword


class ChangePasswordRequest(ApiModel):
    current_password: AnyPassword
    new_password: NewPassword


class Message(ApiModel):
    message: str
