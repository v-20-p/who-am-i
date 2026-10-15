"""Black Zone game API and deterministic development data."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from faker import Faker
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, model_validator

router = APIRouter(prefix="/black-zone", tags=["black-zone"])
UTC_PLUS_THREE = timezone(timedelta(hours=3))
ACCESS_TOKEN = "helloworld"
VALID_USERNAME = "player"
VALID_PASSWORD = "mockpass"


class CaseInsensitiveModel(BaseModel):
    """Accept request keys regardless of casing, matching the legacy API."""

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def normalize_keys(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        fields = {name.casefold(): name for name in cls.model_fields}
        return {
            fields.get(key.casefold(), key) if isinstance(key, str) else key: item
            for key, item in value.items()
        }


class AuthRequest(CaseInsensitiveModel):
    name: str
    passwrd: str
    grantType: str


class BlackZoneDetailsRequest(CaseInsensitiveModel):
    whoIsHeID: str | int | float
    whoAmIID: str | int | float
    whoAmIIDIP: str
    lang: str | None = None


class BlackZoneDetailsFirmRequest(CaseInsensitiveModel):
    id: str | int | float
    whoAmIID: str | int | float
    whoAmIIDIP: str
    lang: str | None = None


def now_timestamp() -> str:
    return datetime.now(UTC_PLUS_THREE).isoformat()


def normalize_id(value: str | int | float) -> str:
    """Convert JSON numeric IDs to their canonical, non-scientific form."""
    if isinstance(value, bool):
        raise ValueError("IDs cannot be booleans")
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError("IDs must be whole numbers")
        value = int(value)
    normalized = str(value).strip()
    if normalized.endswith(".0"):
        normalized = normalized[:-2]
    if not normalized.isdigit():
        raise ValueError("IDs must contain digits only")
    return normalized


def require_player_id(value: str | int | float) -> str:
    player_id = normalize_id(value)
    if len(player_id) != 10 or not player_id.startswith("1"):
        raise HTTPException(400, "whoAmIID must be a 10-digit player ID starting with 1")
    return player_id


def require_entity_id(value: str | int | float, field_name: str) -> str:
    entity_id = normalize_id(value)
    if len(entity_id) != 10:
        raise HTTPException(400, f"{field_name} must be a 10-digit ID")
    return entity_id


def require_token(authorization: str | None) -> None:
    if authorization != f"Bearer {ACCESS_TOKEN}":
        raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Bearer"})


def build_game_data(
    player_count: int = 24, firm_count: int = 12
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    fake = Faker("en_US")
    fake.seed_instance(20261015)

    players: dict[str, dict[str, str]] = {}
    for number in range(player_count):
        player_id = f"2{number + 1:09d}"
        players[player_id] = {
            "id": player_id,
            "displayName": fake.user_name(),
            "fullName": fake.name(),
            "rank": fake.random_element(("Scout", "Runner", "Guardian", "Commander")),
            "faction": "Black Zone",
            "city": fake.city(),
            "joinedAt": fake.date_time_between(
                start_date="-2y", end_date="now", tzinfo=UTC_PLUS_THREE
            ).isoformat(),
        }

    firms: dict[str, dict[str, str]] = {}
    for number in range(firm_count):
        firm_id = f"3{number + 1:09d}"
        firms[firm_id] = {
            "id": firm_id,
            "name": fake.company(),
            "district": fake.city(),
            "faction": "Black Zone",
            "contact": fake.email(),
        }
    return players, firms


PLAYERS, FIRMS = build_game_data()


def build_arabic_game_data() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    """Create Arabic localizations for the seeded Black Zone records."""
    fake = Faker("ar_SA")
    fake.seed_instance(20261015)
    rank_names = {
        "Scout": "كشاف",
        "Runner": "عدّاء",
        "Guardian": "حارس",
        "Commander": "قائد",
    }

    players = {
        player_id: {
            "id": player_id,
            "displayName": fake.user_name(),
            "fullName": fake.name(),
            "rank": rank_names[record["rank"]],
            "faction": "المنطقة السوداء",
            "city": fake.city(),
            "joinedAt": record["joinedAt"],
        }
        for player_id, record in PLAYERS.items()
    }
    firms = {
        firm_id: {
            "id": firm_id,
            "name": fake.company(),
            "district": fake.city(),
            "faction": "المنطقة السوداء",
            "contact": record["contact"],
        }
        for firm_id, record in FIRMS.items()
    }
    return players, firms


AR_PLAYERS, AR_FIRMS = build_arabic_game_data()


def is_arabic(language: str | None) -> bool:

    return bool(language and language.casefold().replace("_", "-").startswith("ar"))


@router.post("/Auth")
async def authenticate(payload: AuthRequest) -> dict[str, str | int]:
    if (
        payload.name != VALID_USERNAME
        or payload.passwrd != VALID_PASSWORD
        or payload.grantType != "password"
    ):
        raise HTTPException(401, "Invalid credentials")

    issued_at = datetime.now(UTC_PLUS_THREE)
    expires_in = 86_400
    return {
        "access_token": ACCESS_TOKEN,
        "token_type": "Bearer",
        "issued_at": issued_at.isoformat(),
        "expires_in": expires_in,
        "expires_on": int((issued_at + timedelta(seconds=expires_in)).timestamp() * 1000),
    }


@router.post("/whoIsHeDetails")
async def who_is_he_details(
    payload: BlackZoneDetailsRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    require_token(authorization)
    require_player_id(payload.whoAmIID)
    player_id = require_entity_id(payload.whoIsHeID, "whoIsHeID")
    player = (AR_PLAYERS if is_arabic(payload.lang) else PLAYERS).get(player_id)
    if player is None:
        raise HTTPException(404, "Black Zone player not found")
    return {**player, "requestTimestamp": now_timestamp(), "responseTimestamp": now_timestamp()}


@router.post("/FirmInfo")
async def firm_info(
    payload: BlackZoneDetailsFirmRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    require_token(authorization)
    require_player_id(payload.whoAmIID)
    firm_id = require_entity_id(payload.id, "id")
    firm = (AR_FIRMS if is_arabic(payload.lang) else FIRMS).get(firm_id)
    if firm is None:
        raise HTTPException(404, "Black Zone firm not found")
    return {**firm, "requestTimestamp": now_timestamp(), "responseTimestamp": now_timestamp()}



@router.get("/health")
async def health_check() -> dict[str, str | int]:
    return {
        "status": "ok",
        "players": len(PLAYERS),
        "firms": len(FIRMS),
        "requestId": secrets.token_hex(8),
    }
