from __future__ import annotations

from datetime import date

from pydantic import BaseModel, EmailStr, Field, field_validator

from .auth_security import normalize_email


class AuthRegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    confirmPassword: str = Field(min_length=8, max_length=128)

    @field_validator('email')
    @classmethod
    def normalize(cls, value: EmailStr) -> str:
        return normalize_email(str(value))


class AuthLoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    rememberMe: bool = False

    @field_validator('email')
    @classmethod
    def normalize(cls, value: EmailStr) -> str:
        return normalize_email(str(value))


class AuthEmailResendIn(BaseModel):
    email: EmailStr

    @field_validator('email')
    @classmethod
    def normalize(cls, value: EmailStr) -> str:
        return normalize_email(str(value))


class AuthResetRequestIn(BaseModel):
    email: EmailStr

    @field_validator('email')
    @classmethod
    def normalize(cls, value: EmailStr) -> str:
        return normalize_email(str(value))


class AuthResetConfirmIn(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    newPassword: str = Field(min_length=8, max_length=128)
    confirmPassword: str = Field(min_length=8, max_length=128)


class AuthOkOut(BaseModel):
    ok: bool = True


class AuthRegisterOut(BaseModel):
    ok: bool = True
    requiresEmailVerification: bool = True
    devEmailPreviewUrl: str | None = None


class AuthResetRequestOut(BaseModel):
    ok: bool = True
    message: str = 'If the email exists, we sent a link.'
    devEmailPreviewUrl: str | None = None


class MeOut(BaseModel):
    id: str
    email: str
    status: str
    role: str
    displayName: str | None = None
    avatarUrl: str | None = None


class ProfileOut(BaseModel):
    firstName: str | None = None
    lastName: str | None = None
    middleName: str | None = None
    birthDate: date | None = None
    birthPlace: str | None = None
    city: str | None = None
    educationType: str | None = None
    educationPlace: str | None = None
    directions: list[str] = Field(default_factory=list)
    university: str | None = None
    eventCode: str | None = None
    desiredSpecialties: str | None = None


class ProfileUpdateIn(BaseModel):
    firstName: str = Field(min_length=1, max_length=120)
    lastName: str = Field(min_length=1, max_length=120)
    middleName: str | None = Field(default=None, max_length=120)
    birthDate: date | None = None
    birthPlace: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, max_length=120)
    educationType: str | None = Field(default=None, max_length=80)
    educationPlace: str | None = Field(default=None, max_length=240)
    directions: list[str] = Field(default_factory=list)
    university: str | None = Field(default=None, max_length=240)
    eventCode: str | None = Field(default=None, max_length=120)
    desiredSpecialties: str | None = Field(default=None, max_length=4000)

    @field_validator("directions")
    @classmethod
    def normalize_directions(cls, value: list[str]) -> list[str]:
        result: list[str] = []
        for item in value:
            text = str(item or "").strip()
            if text:
                result.append(text[:120])
        return result[:20]


class AvatarOut(BaseModel):
    ok: bool = True
    avatarUrl: str | None = None


class ChangePasswordIn(BaseModel):
    currentPassword: str = Field(min_length=1, max_length=128)
    newPassword: str = Field(min_length=8, max_length=128)
    confirmPassword: str = Field(min_length=8, max_length=128)


class CompetencyItemOut(BaseModel):
    code: str
    title: str
    level: float
    delta: float
    progress: float
    color: str


class CompetenciesSummaryOut(BaseModel):
    items: list[CompetencyItemOut] = Field(default_factory=list)
    empty: bool = False
