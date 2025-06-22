from pydantic import BaseModel, EmailStr, ConfigDict, field_validator

from database.validators.accounts import validate_password_strength


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
    pass


class UserRegistrationResponseSchema(BaseModel):
    id: int
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class UserLoginRequestSchema(BaseEmailPasswordSchema):
    pass


class PasswordResetRequestSchema(BaseModel):
    email: EmailStr


class ResendActivationTokenRequestSchema(PasswordResetRequestSchema):
    pass


class PasswordResetCompleteRequestSchema(BaseEmailPasswordSchema):
    token: str


class UserLoginResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequestSchema(BaseModel):
    refresh_token: str


class TokenRefreshResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenVerifyRequestSchema(BaseModel):
    access_token: str


class UserActivationRequestSchema(BaseModel):
    email: EmailStr
    token: str


class MessageResponseSchema(BaseModel):
    message: str
