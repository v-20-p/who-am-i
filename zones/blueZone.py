"""Blue Zone game API with deterministic English and Arabic Faker data."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from faker import Faker
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, model_validator

router = APIRouter(prefix="/blue-zone", tags=["blue-zone"])
UTC_PLUS_THREE = timezone(timedelta(hours=3))
ACCESS_TOKEN = "bluezone-token"
VALID_USERNAME = "player"
VALID_PASSWORD = "mockpass"


class CaseInsensitiveModel(BaseModel):
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


class PlayerDetailsRequest(CaseInsensitiveModel):
    whoIsHeID: str | int | float
    whoAmIID: str | int | float
    whoAmIIDIP: str
    lang: str | None = None


class FirmDetailsRequest(CaseInsensitiveModel):
    id: str | int | float
    whoAmIID: str | int | float
    whoAmIIDIP: str
    lang: str | None = None


def now_timestamp() -> str:
    return datetime.now(UTC_PLUS_THREE).isoformat()


def normalize_id(value: str | int | float) -> str:
    if isinstance(value, bool):
        raise ValueError("IDs cannot be booleans")
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError("IDs must be whole numbers")
        value = int(value)
    identifier = str(value).strip()
    if identifier.endswith(".0"):
        identifier = identifier[:-2]
    if not identifier.isdigit():
        raise ValueError("IDs must contain digits only")
    return identifier


def require_citizen_id(value: str | int | float) -> str:
    citizen_id = normalize_id(value)
    if len(citizen_id) != 10 or not citizen_id.startswith("1"):
        raise HTTPException(400, "whoAmIID must be a 10-digit citizen ID starting with 1")
    return citizen_id


def require_entity_id(value: str | int | float, field_name: str) -> str:
    entity_id = normalize_id(value)
    if len(entity_id) != 10:
        raise HTTPException(400, f"{field_name} must be a 10-digit ID")
    return entity_id


def require_token(authorization: str | None) -> None:
    if authorization != f"Bearer {ACCESS_TOKEN}":
        raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Bearer"})


def is_arabic(language: str | None) -> bool:
    return bool(language and language.casefold().replace("_", "-").startswith("ar"))


def build_game_data() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    fake = Faker("en_US")
    fake.seed_instance(20261016)
    players: dict[str, dict[str, str]] = {}
    for number in range(24):
        player_id = f"4{number + 1:09d}"
        players[player_id] = {
            "id": player_id,
            "displayName": fake.user_name(),
            "fullName": fake.name(),
            "rank": fake.random_element(("Navigator", "Engineer", "Sentinel", "Captain")),
            "faction": "Blue Zone",
            "city": fake.city(),
            "joinedAt": fake.date_time_between(start_date="-2y", end_date="now", tzinfo=UTC_PLUS_THREE).isoformat(),
        }
    firms: dict[str, dict[str, str]] = {}
    for number in range(12):
        firm_id = f"5{number + 1:09d}"
        firms[firm_id] = {
            "id": firm_id,
            "name": fake.company(),
            "district": fake.city(),
            "faction": "Blue Zone",
            "contact": fake.email(),
        }
    return players, firms


PLAYERS, FIRMS = build_game_data()


def build_arabic_game_data() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    fake = Faker("ar_SA")
    fake.seed_instance(20261016)
    ranks = {"Navigator": "ملاح", "Engineer": "مهندس", "Sentinel": "حارس", "Captain": "قائد"}
    players = {
        player_id: {
            "id": player_id,
            "displayName": fake.user_name(),
            "fullName": fake.name(),
            "rank": ranks[record["rank"]],
            "faction": "المنطقة الزرقاء",
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
            "faction": "المنطقة الزرقاء",
            "contact": record["contact"],
        }
        for firm_id, record in FIRMS.items()
    }
    return players, firms


AR_PLAYERS, AR_FIRMS = build_arabic_game_data()


@router.post("/Auth")
async def authenticate(payload: AuthRequest) -> dict[str, str | int]:
    if payload.name != VALID_USERNAME or payload.passwrd != VALID_PASSWORD or payload.grantType != "password":
        raise HTTPException(401, "Invalid credentials")
    issued_at = datetime.now(UTC_PLUS_THREE)
    return {
        "access_token": ACCESS_TOKEN,
        "token_type": "Bearer",
        "issued_at": issued_at.isoformat(),
        "expires_in": 86_400,
        "expires_on": int((issued_at + timedelta(days=1)).timestamp() * 1000),
    }


@router.post("/whoIsHeDetails")
async def who_is_he_details(payload: PlayerDetailsRequest, authorization: str | None = Header(default=None)) -> dict[str, str]:
    require_token(authorization)
    require_citizen_id(payload.whoAmIID)
    player_id = require_entity_id(payload.whoIsHeID, "whoIsHeID")
    player = (AR_PLAYERS if is_arabic(payload.lang) else PLAYERS).get(player_id)
    if player is None:
        raise HTTPException(404, "Blue Zone player not found")
    return {**player, "requestTimestamp": now_timestamp(), "responseTimestamp": now_timestamp()}


@router.get("/health")
async def health_check() -> dict[str, str | int]:
    return {"status": "ok", "players": len(PLAYERS), "firms": len(FIRMS), "requestId": secrets.token_hex(8)}
