from pydantic import Field

from backend.core.schemas import Revisioned, Schema
from backend.modules.profiles.schemas import Profile


class Privacy(Schema):
    discoverable: bool = True
    allow_in_paths: bool = True
    employment_visible: bool = True
    skills_visible: bool = True


class PrivacyUpdate(Privacy):
    discoverable: bool
    allow_in_paths: bool
    employment_visible: bool
    skills_visible: bool


class UserPatch(Schema):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    profile: Profile | None = None


class User(Revisioned):
    email: str
    display_name: str
    roles: list[str]
    status: str
    deleted_at: str | None
    privacy: Privacy
    profile: Profile
