# Who Am I API

A minimal FastAPI service.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for interactive API documentation.

## Endpoints

- `GET /` — welcome message
- `GET /health` — health check
