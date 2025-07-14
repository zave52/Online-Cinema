from pydantic import BaseModel, EmailStr, ConfigDict, field_validator

from database.models.accounts import UserGroupEnum
from database.validators.accounts import validate_password_strength

from .exapmles.accounts import (
    user_registration_request_schema_example,
    user_registration_response_schema_example,
    user_login_request_schema_example,
    user_login_response_schema_example,
    password_reset_request_schema_example,
    resend_activation_token_request_schema_example,
    password_reset_complete_request_schema_example,
    password_change_request_schema_example,
    token_refresh_request_schema_example,
    token_refresh_response_schema_example,
    token_verify_request_schema_example,
    user_activation_request_schema_example,
    user_group_update_request_schema_example,
    user_manual_activation_schema_example,
    message_response_schema_example
)


class BaseEmailPasswordSchema(BaseModel):
    email: EmailStr
    password: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


class UserRegistrationRequestSchema(BaseEmailPasswordSchema):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": user_registration_request_schema_example
        }
    )


class UserRegistrationResponseSchema(BaseModel):
    id: int
    email: EmailStr

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": user_registration_response_schema_example
        }
    )


class UserLoginRequestSchema(BaseEmailPasswordSchema):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": user_login_request_schema_example
        }
    )


class PasswordResetRequestSchema(BaseModel):
    email: EmailStr

    model_config = ConfigDict(
        json_schema_extra={
            "example": password_reset_request_schema_example
        }
    )


class ResendActivationTokenRequestSchema(PasswordResetRequestSchema):
    model_config = ConfigDict(
        json_schema_extra={
            "example": resend_activation_token_request_schema_example
        }
    )


class PasswordResetCompleteRequestSchema(BaseEmailPasswordSchema):
    token: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": password_reset_complete_request_schema_example
        }
    )


class PasswordChangeRequestSchema(BaseModel):
    old_password: str
    new_password: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": password_change_request_schema_example
        }
    )

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


class UserLoginResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    model_config = ConfigDict(
        json_schema_extra={
            "example": user_login_response_schema_example
        }
    )


class TokenRefreshRequestSchema(BaseModel):
    refresh_token: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": token_refresh_request_schema_example
        }
    )


class TokenRefreshResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"

    model_config = ConfigDict(
        json_schema_extra={
            "example": token_refresh_response_schema_example
        }
    )


class TokenVerifyRequestSchema(BaseModel):
    access_token: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": token_verify_request_schema_example
        }
    )


class UserActivationRequestSchema(BaseModel):
    email: EmailStr
    token: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": user_activation_request_schema_example
        }
    )


class MessageResponseSchema(BaseModel):
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": message_response_schema_example
        }
    )


class UserGroupUpdateRequestSchema(BaseModel):
    group_name: UserGroupEnum

    model_config = ConfigDict(
        json_schema_extra={
            "example": user_group_update_request_schema_example
        }
    )


class UserManualActivationSchema(BaseModel):
    email: EmailStr

    model_config = ConfigDict(
        json_schema_extra={
            "example": user_manual_activation_schema_example
        }
    )
