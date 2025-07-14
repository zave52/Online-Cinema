from datetime import date
from typing import Optional

from fastapi import UploadFile, Form, HTTPException
from pydantic import BaseModel, field_validator, HttpUrl, ConfigDict

from validation.profiles import (
    validate_name,
    validate_image,
    validate_gender,
    validate_birth_date
)

from .exapmles.profiles import (
    profile_create_request_schema_example,
    profile_update_request_schema_example,
    profile_patch_request_schema_example,
    profile_response_schema_example,
    profile_retrieve_schema_example,
    message_response_schema_example
)


class ProfileBaseModel(BaseModel):
    first_name: str
    last_name: str
    gender: str
    date_of_birth: date
    info: str


class ProfileCreateRequestSchema(ProfileBaseModel):
    avatar: UploadFile

    model_config = ConfigDict(
        json_schema_extra={
            "example": profile_create_request_schema_example
        }
    )

    @classmethod
    def from_form(
        cls,
        first_name: str = Form(...),
        last_name: str = Form(...),
        avatar: UploadFile = Form(...),
        gender: str = Form(...),
        date_of_birth: date = Form(...),
        info: str = Form(...)
    ) -> "ProfileCreateRequestSchema":
        return cls(
            first_name=first_name,
            last_name=last_name,
            avatar=avatar,
            gender=gender,
            date_of_birth=date_of_birth,
            info=info
        )

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_email(cls, name: str, info) -> str:
        try:
            validate_name(name)
            return name.lower()
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=[{
                    "type": "value_error",
                    "loc": [info.field_name],
                    "msg": str(e),
                    "input": name
                }]
            )

    @field_validator("avatar")
    @classmethod
    def validate_avatar(cls, avatar: UploadFile) -> UploadFile:
        try:
            validate_image(avatar)
            return avatar
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=[{
                    "type": "value_error",
                    "loc": ["avatar"],
                    "msg": str(e),
                    "input": avatar.filename
                }]
            )

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, gender: str) -> str:
        try:
            validate_gender(gender)
            return gender
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=[{
                    "type": "value_error",
                    "loc": ["gender"],
                    "msg": str(e),
                    "input": gender
                }]
            )

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, date_of_birth: date) -> date:
        try:
            validate_birth_date(date_of_birth)
            return date_of_birth
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=[{
                    "type": "value_error",
                    "loc": ["date_of_birth"],
                    "msg": str(e),
                    "input": str(date_of_birth)
                }]
            )

    @field_validator("info")
    @classmethod
    def validate_info(cls, info: str) -> str:
        cleaned_info = info.strip()
        if not cleaned_info:
            raise HTTPException(
                status_code=422,
                detail=[{
                    "type": "value_error",
                    "loc": ["info"],
                    "msg": "Info field cannot be empty or contain only spaces.",
                    "input": info
                }]
            )
        return cleaned_info


class ProfileUpdateRequestSchema(ProfileBaseModel):
    avatar: Optional[UploadFile] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": profile_update_request_schema_example
        }
    )

    @classmethod
    def from_form(
        cls,
        first_name: str = Form(...),
        last_name: str = Form(...),
        gender: str = Form(...),
        date_of_birth: date = Form(...),
        info: str = Form(...),
        avatar: Optional[UploadFile] = Form(None)
    ) -> "ProfileUpdateRequestSchema":
        return cls(
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            date_of_birth=date_of_birth,
            info=info,
            avatar=avatar
        )

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, name: str, info) -> str:
        try:
            validate_name(name)
            return name.lower()
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=[{
                    "type": "value_error",
                    "loc": [info.field_name],
                    "msg": str(e),
                    "input": name
                }]
            )

    @field_validator("avatar")
    @classmethod
    def validate_avatar(
        cls,
        avatar: Optional[UploadFile]
    ) -> Optional[UploadFile]:
        if avatar is None:
            return None
        try:
            validate_image(avatar)
            return avatar
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=[{
                    "type": "value_error",
                    "loc": ["avatar"],
                    "msg": str(e),
                    "input": avatar.filename
                }]
            )

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, gender: str) -> str:
        try:
            validate_gender(gender)
            return gender
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=[{
                    "type": "value_error",
                    "loc": ["gender"],
                    "msg": str(e),
                    "input": gender
                }]
            )

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, date_of_birth: date) -> date:
        try:
            validate_birth_date(date_of_birth)
            return date_of_birth
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=[{
                    "type": "value_error",
                    "loc": ["date_of_birth"],
                    "msg": str(e),
                    "input": str(date_of_birth)
                }]
            )

    @field_validator("info")
    @classmethod
    def validate_info(cls, info: str) -> str:
        cleaned_info = info.strip()
        if not cleaned_info:
            raise HTTPException(
                status_code=422,
                detail=[{
                    "type": "value_error",
                    "loc": ["info"],
                    "msg": "Info field cannot be empty or contain only spaces.",
                    "input": info
                }]
            )
        return cleaned_info


class ProfilePatchRequestSchema(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    info: Optional[str] = None
    avatar: Optional[UploadFile] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": profile_patch_request_schema_example
        }
    )

    @classmethod
    def from_form(
        cls,
        first_name: Optional[str] = Form(None),
        last_name: Optional[str] = Form(None),
        gender: Optional[str] = Form(None),
        date_of_birth: Optional[date] = Form(None),
        info: Optional[str] = Form(None),
        avatar: Optional[UploadFile] = Form(None)
    ) -> "ProfilePatchRequestSchema":
        return cls(
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            date_of_birth=date_of_birth,
            info=info,
            avatar=avatar
        )

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, name: Optional[str], info) -> Optional[str]:
        if name is None:
            return None
        try:
            validate_name(name)
            return name.lower()
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=[{
                    "type": "value_error",
                    "loc": [info.field_name],
                    "msg": str(e),
                    "input": name
                }]
            )

    @field_validator("avatar")
    @classmethod
    def validate_avatar(
        cls,
        avatar: Optional[UploadFile]
    ) -> Optional[UploadFile]:
        if avatar is None:
            return None
        try:
            validate_image(avatar)
            return avatar
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=[{
                    "type": "value_error",
                    "loc": ["avatar"],
                    "msg": str(e),
                    "input": avatar.filename
                }]
            )

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, gender: Optional[str]) -> Optional[str]:
        if gender is None:
            return None
        try:
            validate_gender(gender)
            return gender
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=[{
                    "type": "value_error",
                    "loc": ["gender"],
                    "msg": str(e),
                    "input": gender
                }]
            )

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(
        cls,
        date_of_birth: Optional[date]
    ) -> Optional[date]:
        if date_of_birth is None:
            return None
        try:
            validate_birth_date(date_of_birth)
            return date_of_birth
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=[{
                    "type": "value_error",
                    "loc": ["date_of_birth"],
                    "msg": str(e),
                    "input": str(date_of_birth)
                }]
            )

    @field_validator("info")
    @classmethod
    def validate_info(cls, info: Optional[str]) -> Optional[str]:
        if info is None:
            return None
        cleaned_info = info.strip()
        if not cleaned_info:
            raise HTTPException(
                status_code=422,
                detail=[{
                    "type": "value_error",
                    "loc": ["info"],
                    "msg": "Info field cannot be empty or contain only spaces.",
                    "input": info
                }]
            )
        return cleaned_info


class ProfileResponseSchema(ProfileBaseModel):
    id: int
    user_id: int
    avatar: HttpUrl

    model_config = ConfigDict(
        json_schema_extra={
            "example": profile_response_schema_example
        }
    )


class ProfileRetrieveSchema(ProfileResponseSchema):
    email: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": profile_retrieve_schema_example
        }
    )


class MessageResponseSchema(BaseModel):
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": message_response_schema_example
        }
    )
