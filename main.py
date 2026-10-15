import uvicorn
from fastapi import FastAPI

app = FastAPI(title="Who Am I API", version="0.1.0")


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Return a simple service health response."""
    return {"status": "ok"}


@app.get("/", tags=["root"])
def read_root() -> dict[str, str]:
    return {"message": "Welcome to Who Am I API"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)