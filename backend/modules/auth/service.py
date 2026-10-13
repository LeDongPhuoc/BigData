import re
import secrets
from uuid import uuid4

from backend.core.errors import ApiError, require
from backend.core.policy import active_user, actor_check
from backend.core.repository import Repository
from backend.core.security import (
    access_token,
    deadline,
    digest,
    dummy_hash,
    hash_password,
    token_equal,
    verify_password,
)
from backend.core.transactions import transaction
from backend.core.workflow import audit, quota
from backend.modules.auth.repository import AuthRepository
from backend.modules.users.repository import UserRepository
from backend.modules.users.schemas import Privacy, Profile
from database.migrate import utc_now


class AuthService:
    def __init__(self, db, config, request_id):
        self.db, self.config, self.request_id = db, config, request_id

    def throttle(self, ip, operation):
        maximum, period = {
            "login": (self.config.login_limit, 60),
            "register": (self.config.register_limit, 3600),
            "refresh": (self.config.refresh_limit, 60),
        }[operation]
        with transaction(self.db) as tx:
            quota(
                tx,
                digest(ip),
                operation,
                maximum,
                period,
            )

    def issue(self, tx, user, family=None):
        repo = Repository(tx)
        repo.collection = "auth_families"
        if family is None:
            family = repo.insert(
                {
                    "user_id": user["_id"],
                    "expires_at": deadline(self.config.refresh_seconds),
                    "revoked_at": None,
                }
            )
        session_key = uuid4().hex
        opaque = session_key + "." + secrets.token_urlsafe(48)
        repo.collection = "auth_sessions"
        repo.insert(
            {
                "_key": session_key,
                "user_id": user["_id"],
                "family_id": family["_id"],
                "token_hash": digest(opaque),
                "status": "active",
                "expires_at": family["expires_at"],
                "used_at": None,
                "revoked_at": None,
            }
        )
        return {
            "access_token": access_token(self.config, user["_key"], family["_key"]),
            "refresh_token": opaque,
            "expires_in": self.config.access_seconds,
            "token_type": "bearer",
        }

    def register(self, data, ip):
        self.throttle(ip, "register")
        encoded = hash_password(data.password)
        with transaction(self.db) as tx:
            require(
                UserRepository(tx).by_email(data.email) is None,
                409,
                "duplicate_email",
                "Email already registered",
            )
            user = UserRepository(tx).insert(
                {
                    "email": data.email,
                    "display_name": data.display_name,
                    "roles": ["candidate"],
                    "status": "active",
                    "deleted_at": None,
                    "privacy": Privacy().model_dump(),
                    "profile": Profile().model_dump(),
                },
            )
            AuthRepository(tx).insert({"user_id": user["_id"], "password_hash": encoded})
            audit(tx, user["_id"], "auth.register", user["_id"], self.request_id)
            return self.issue(tx, user)

    def login(self, data, ip):
        self.throttle(ip, "login")
        user = UserRepository(self.db).by_email(data.email)
        cred = AuthRepository(self.db).credential(user["_id"]) if user else None
        valid = verify_password(cred["password_hash"] if cred else dummy_hash, data.password)
        require(valid and cred, 401, "unauthenticated", "Invalid credentials")
        with transaction(self.db) as tx:
            user = active_user(tx, user["_id"])
            current = AuthRepository(tx).credential(user["_id"])
            require(
                current["_rev"] == cred["_rev"],
                401,
                "unauthenticated",
                "Credentials changed; sign in again",
            )
            audit(tx, user["_id"], "auth.login", user["_id"], self.request_id)
            return self.issue(tx, user)

    def refresh(self, opaque, ip):
        self.throttle(ip, "refresh")
        session_key = opaque.split(".", 1)[0]
        require(
            re.fullmatch(r"[a-f0-9]{32}", session_key),
            401,
            "unauthenticated",
            "Invalid refresh credentials",
        )
        replay = False
        result = None
        with transaction(self.db) as tx:
            repo = AuthRepository(tx)
            session = repo.session(session_key)
            require(
                session and token_equal(session["token_hash"], digest(opaque)),
                401,
                "unauthenticated",
                "Invalid refresh credentials",
            )
            family = repo.family(session["family_id"])
            require(
                family and family["revoked_at"] is None and family["expires_at"] > utc_now(),
                401,
                "unauthenticated",
                "Refresh session unavailable",
            )
            user = active_user(tx, session["user_id"])
            if session["status"] != "active":
                # Commit replay revocation before raising 401 outside the transaction.
                tx.collection("auth_families").update(
                    {"_key": family["_key"], "revoked_at": utc_now(), "updated_at": utc_now()},
                )
                audit(tx, user["_id"], "auth.refresh_reuse", family["_id"], self.request_id)
                replay = True
            else:
                tx.collection("auth_sessions").update(
                    {
                        "_key": session_key,
                        "status": "used",
                        "used_at": utc_now(),
                        "updated_at": utc_now(),
                    },
                )
                result = self.issue(tx, user, family)
        if replay:
            raise ApiError(401, "refresh_reuse", "Refresh reuse detected; sign in again")
        return result

    def logout(self, actor, opaque=None):
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            if opaque is not None:
                session_key = opaque.split(".", 1)[0]
                require(
                    re.fullmatch(r"[a-f0-9]{32}", session_key),
                    401,
                    "unauthenticated",
                    "Invalid refresh credentials",
                )
                session = AuthRepository(tx).session(session_key)
                require(
                    session and token_equal(session["token_hash"], digest(opaque)),
                    401,
                    "unauthenticated",
                    "Invalid refresh credentials",
                )
                require(session["family_id"] == "auth_families/" + actor["session_id"])
            now = utc_now()
            tx.collection("auth_families").update(
                {"_key": actor["session_id"], "revoked_at": now, "updated_at": now},
            )
            audit(tx, user["_id"], "auth.logout", user["_id"], self.request_id)
