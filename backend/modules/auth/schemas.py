from pydantic import EmailStr, Field, field_validator

from backend.core.schemas import Schema


class Login(Schema):
    # Login accepts the ASCII format already persisted by the database, including
    # the reserved .test domain used by demo accounts. Registration is stricter below.
    email: str = Field(
        min_length=3,
        max_length=254,
        pattern=r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$",
    )
    # Password whitespace is significant; never silently normalize it.
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value):
        result = str(value).lower()
        if not result.isascii():
            raise ValueError("Email must use ASCII characters")
        return result

    @field_validator("password", mode="before")
    @classmethod
    def preserve_password(cls, value):
        # Config below disables stripping for the entire auth input.
        return value

    model_config = {"extra": "forbid", "str_strip_whitespace": False}


class Register(Login):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)

    @field_validator("display_name")
    @classmethod
    def name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("display_name must not be empty")
        return value


class Refresh(Schema):
    refresh_token: str = Field(min_length=32, max_length=256)


class Tokens(Schema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
