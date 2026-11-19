# Kathmandu Waste Management — API and waste classifier

Backend for the Next.js app in [`../waste-management-website`](../waste-management-website): one site with Citizen, Driver, Ward staff and KMC staff sections.

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

| Section | Email |
| --- | --- |
| Citizen | asha.gurung@example.com (Ward 17) |
| Driver | ram.thapa@kathmandu.gov.np, or first.last@kathmandu.gov.np for any driver |
| Ward | ward17@kathmandu.gov.np (Ward 17 has the detailed demo data) |
| KMC | anita.shrestha@kathmandu.gov.np |

Older databases are upgraded on startup: missing columns are added (`app/database.py`) and stops, driver and citizen accounts and starting truck positions are seeded if absent.

Or with Docker (Postgres, weights baked into the model image): `docker compose up --build`.

## Configuration

See `.env.example`. The important ones:

- `CORS_ORIGINS` — comma-separated browser origins allowed to call the API (default `http://localhost:3000,http://127.0.0.1:3000`). Add the deployed frontend's origin here. `CORS_ORIGIN_REGEX` allows patterns.
- `MODEL_SERVICE_URL` — where the backend sends photos (default `http://localhost:8001`).
- `DATABASE_URL` — SQLite by default; `postgresql+asyncpg://...` in Docker.
- `SEED_ON_STARTUP` — seed demo data into an empty database (default on). `python backend/seed_db.py --reset` re-seeds.
- `SMS_PROVIDER` — `dummy` (default) or `sparrow`. See [SMS alerts](#sms-alerts).

## SMS alerts

Residents subscribe per ward (staff add them on the **SMS Alerts** page). They are texted automatically when a driver reports a delayed route, when a route's or ward's collection time changes, and when an awareness program is announced; staff can also broadcast a message or send a test to one number. Every message is stored (`sms_messages`) and shown in the page's outbox.

The default `SMS_PROVIDER=dummy` sends nothing: each message is written to the backend log (`app.sms: [dummy] SMS to +977…`) and recorded as sent. To send real messages:

1. Get a token and an approved sender identity from [Sparrow SMS](https://sparrowsms.com).
2. Set `SMS_PROVIDER=sparrow`, `SPARROW_SMS_TOKEN=…` and `SMS_SENDER=…`, restart the backend.
3. Send a test to your own number from the SMS Alerts page before broadcasting. `SparrowProvider` in `backend/app/sms.py` follows Sparrow's v2 API but has not been tried against the live gateway; check the outbox's error column if a send fails.

Another gateway (Aakash SMS, Twilio, …) is a class with `name` and `async send(phone, text)` added to `provider()` in `app/sms.py`. Sends happen inside the request, one number at a time, which is fine for ward-sized lists; move them to a background job before broadcasting to thousands.

Demo subscribers use fake `98000000xx` numbers (`backend/app/seed_data/sms_subscribers.json`).

## Feature demo

`docs/feature-demo/` has screenshots and logs of the camera and SMS features (see its README).

## API

Interactive docs: http://localhost:8000/docs. All routes are under `/api/v1` and, except login/signup/identify, need `Authorization: Bearer <token>`. Responses use the frontend's field names (`src/types`).

| Area | Endpoints |
| --- | --- |
| Auth | `POST /auth/login`, `POST /auth/signup` (`{email, password, portal: "kmc"\|"ward"\|"citizen"\|"driver"}`; citizens also send `ward` and optionally `phone`), `GET/PATCH /me` (ward staff and citizens set their ward here), `POST /me/password` |
| Ward portal | `GET /wards/{n}/state`; `POST /wards/{n}/routes/{r}/start`, `/driver-update`; `PATCH /wards/{n}/routes/{r}` (vehicle, time); `POST /wards/{n}/vehicles`, `/programs`, `/updates`, `/reports` |
| KMC portal | `GET /kmc/state`; `POST /kmc/wards/{n}/complete`, `/restart`; `PUT /kmc/wards/{n}/assignment`, `/schedule`; `POST /kmc/vehicles`, `/programs`, `/updates` |
| Shared | `PATCH /vehicles/{id}`; `POST /programs/{id}/decision`, `/resubmit`, `/start`, `/complete`, `/register`; `PATCH /reports/{id}` |
| Identify | `POST /identify` (multipart `image`, optional `ward`, `save=false` for live-video frames that should not be stored; login optional) → `{label, category, confidence, probabilities}`; `GET /identifications?ward=` → recent items + counts |
| SMS | `GET /sms?ward=` (subscribers, outbox, counts, provider); `POST /sms/subscribers` (`{name, phone, ward}`), `DELETE /sms/subscribers/{id}`; `POST /sms/send` (`{message, ward?, phone?}`: broadcast to a ward, to every ward (KMC), or a test to one number) |
| Live map | `GET /live?ward=` → routes with stops (`lat`, `lng`, `status`), vehicles with their last GPS fix. Citizens get their own ward; ward staff theirs; KMC any or all. `GET /uploads/{name}`: report photos |
| Citizen | `GET /citizen/state`; `POST /citizen/reports` (multipart: `type`, `category`, `description`, `location`, `route`, optional `photo`); `POST/DELETE /citizen/programs/{id}/register`; `PUT /citizen/reminder` (`{enabled, phone?}`, subscribes the phone to the ward's SMS alerts) |
| Driver | `GET /driver/state` (routes of the vehicles whose driver is this account's name); `POST /driver/routes/{id}/start`, `/finish` (`{outcome, kg}`); `POST /driver/stops/{id}` (`{status: Pending\|Collected\|Skipped}`); `POST /driver/location` (`{lat, lng, accuracy?, heading?, speed?, vehicle?}`); `POST /driver/issues` |
| Health | `GET /health` (also reports the model service status) |

Ward staff can only read and change their own ward; KMC staff can access every ward. Citizens and drivers cannot use the staff endpoints (ward, KMC, shared, SMS); citizens see only their own reports and identifications. Report status changes are kept in each report's `history` and notify the citizen who filed it. Changes made in one portal show up in the other (for example a delayed route in a ward notifies KMC, and a KMC schedule change posts an update to the ward).

Model service: `POST /classify` (multipart `image`, JPEG/PNG/WebP/HEIC, max 10 MB) and `GET /health`.

## Tests

```bash
uv pip install -p backend/.venv/bin/python -r tests/requirements.txt
backend/.venv/bin/python -m pytest
```

The tests use a temporary SQLite database and a stubbed classifier, so they do not need the model service.
