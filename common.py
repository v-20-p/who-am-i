

import re
import base64
import asyncio
from fastapi import Request, Response

# Flip to False only to bypass auth while debugging something else.
REQUIRE_AUTH = True
VALID_USER = "user"
VALID_PASS = "mockpass"

# Seconds added to every response. Raise it to shake out timeout handling.
LATENCY = 0.0


def tag(body: str, name: str) -> str:

    m = re.search(rf"<(?:\w+:)?{name}\b[^>]*>(.*?)</(?:\w+:)?{name}>", body, re.S)
    return m.group(1).strip() if m else ""


def attr(body: str, element: str, name: str) -> str:

    m = re.search(rf'<{element}[^>]*\b{name}\s*=\s*"([^"]*)"', body)
    return m.group(1) if m else ""


def has(body: str, needle: str) -> bool:
    return needle in body


async def read_body(request: Request) -> str:

    raw = await request.body()
    return raw.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

def xml(content: str, status: int = 200) -> Response:
    return Response(content=content, status_code=status,
                    media_type="text/xml; charset=utf-8")


def challenge() -> Response:

    return Response(content="<error>unauthorized</error>", status_code=401,
                    media_type="text/xml",
                    headers={"WWW-Authenticate": 'Basic realm="mock"'})


def authorized(request: Request) -> bool:
    if not REQUIRE_AUTH:
        return True
    hdr = request.headers.get("authorization", "")
    if not hdr.startswith("Basic "):
        return False
    try:
        user, _, pwd = base64.b64decode(hdr[6:]).decode().partition(":")
    except Exception:
        return False
    return user == VALID_USER and pwd == VALID_PASS


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

def scenario(identifier: str) -> str:

    if identifier.endswith("9999"):
        return "timeout"
    if identifier.endswith("8888"):
        return "fault"
    if identifier.endswith("0000"):
        return "notfound"
    return "ok"


async def hang():
    await asyncio.sleep(300)


async def delay():
    if LATENCY:
        await asyncio.sleep(LATENCY)


def log(client: str, **fields):

    parts = " ".join(f"{k}={v}" for k, v in fields.items())
    print(f"[{client}] {parts}")


