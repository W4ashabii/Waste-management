# Kathmandu Waste Management — API and waste classifier

Backend for the Next.js app in [`../waste-management-website`](../waste-management-website) (KMC and ward staff portals).

| Part | Path | Port |
| --- | --- | --- |
| Backend API (FastAPI, SQLAlchemy async) | `backend/` | 8000 |
| Model service: local [W4ashabii/waste_classifier](https://huggingface.co/W4ashabii/waste_classifier) (YOLOv8s-cls, `Bio` / `Non_Bio`) | `model-service/` | 8001 |
| Frontend (Next.js) | `../waste-management-website` | 3000 |

## Run locally

```bash
./run_local.sh
```

Needs [uv](https://docs.astral.sh/uv/) and Node.js. It creates the virtualenvs, starts all three services and uses SQLite (`backend/waste_management.db`). The first start downloads `best.pt` (~10 MB) from Hugging Face into `model-service/weights/`; after that the model runs offline. Set `WEIGHTS_PATH` to use a weights file you already have.

Demo logins (password `demo1234`):

| Portal | Email |
| --- | --- |
| KMC | anita.shrestha@kathmandu.gov.np |
| Ward | ward17@kathmandu.gov.np (Ward 17 has the detailed demo data) |

Or with Docker (Postgres, weights baked into the model image): `docker compose up --build`.

## Configuration

See `.env.example`. The important ones:

- `CORS_ORIGINS` — comma-separated browser origins allowed to call the API (default `http://localhost:3000,http://127.0.0.1:3000`). Add the deployed frontend's origin here. `CORS_ORIGIN_REGEX` allows patterns.
- `MODEL_SERVICE_URL` — where the backend sends photos (default `http://localhost:8001`).
- `DATABASE_URL` — SQLite by default; `postgresql+asyncpg://...` in Docker.
- `SEED_ON_STARTUP` — seed demo data into an empty database (default on). `python backend/seed_db.py --reset` re-seeds.

## API

Interactive docs: http://localhost:8000/docs. All routes are under `/api/v1` and, except login/signup/identify, need `Authorization: Bearer <token>`. Responses use the frontend's field names (`src/types`).

| Area | Endpoints |
| --- | --- |
| Auth | `POST /auth/login`, `POST /auth/signup` (`{email, password, portal: "kmc"\|"ward"}`), `GET/PATCH /me` (ward staff set their ward here), `POST /me/password` |
| Ward portal | `GET /wards/{n}/state`; `POST /wards/{n}/routes/{r}/start`, `/driver-update`; `PATCH /wards/{n}/routes/{r}` (vehicle, time); `POST /wards/{n}/vehicles`, `/programs`, `/updates`, `/reports` |
| KMC portal | `GET /kmc/state`; `POST /kmc/wards/{n}/complete`, `/restart`; `PUT /kmc/wards/{n}/assignment`, `/schedule`; `POST /kmc/vehicles`, `/programs`, `/updates` |
| Shared | `PATCH /vehicles/{id}`; `POST /programs/{id}/decision`, `/resubmit`, `/start`, `/complete`, `/register`; `PATCH /reports/{id}` |
| Identify | `POST /identify` (multipart `image`, optional `ward`; login optional) → `{label, category, confidence, probabilities}`; `GET /identifications?ward=` → recent items + counts |
| Health | `GET /health` (also reports the model service status) |

Ward staff can only read and change their own ward; KMC staff can access every ward. Changes made in one portal show up in the other (for example a delayed route in a ward notifies KMC, and a KMC schedule change posts an update to the ward).

Model service: `POST /classify` (multipart `image`, JPEG/PNG/WebP/HEIC, max 10 MB) and `GET /health`.

## Tests

```bash
uv pip install -p backend/.venv/bin/python -r tests/requirements.txt
backend/.venv/bin/python -m pytest
```

The tests use a temporary SQLite database and a stubbed classifier, so they do not need the model service.
