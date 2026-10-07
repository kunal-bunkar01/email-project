# Backend

FastAPI application for Sable. The root [README](../README.md) is the setup guide. This file is the short backend reference.

## Run

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

On macOS or Linux, activate with `source venv/bin/activate`.

The API listens on http://localhost:8000. Interactive docs are at http://localhost:8000/docs.

SQLite is created at `data/email_assistant.db` on startup.

## Demo mode

Leave `DEMO_MODE=true` in `.env` (or omit `.env` entirely; demo mode is the default). The sample inbox is inserted once. Gmail and OpenAI are not called.

## Credentials

Put secrets in `.env`, copied from `.env.example`.

Google's downloaded client file, if you use one, goes here:

```text
credentials/client_secret.json
```

That folder is gitignored. The environment variables `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are preferred.

## Main routes

```text
GET  /api/health
GET  /api/auth/status
GET  /api/auth/google
GET  /api/auth/google/callback
POST /api/auth/logout
POST /api/emails/sync
GET  /api/emails
GET  /api/emails/{id}
POST /api/emails/{id}/process
POST /api/emails/{id}/regenerate
GET  /api/reviews
GET  /api/reviews/{id}
PUT  /api/drafts/{id}
POST /api/drafts/{id}/approve
POST /api/drafts/{id}/reject
POST /api/drafts/{id}/send
GET  /api/dashboard/stats
GET  /api/activity
GET  /api/settings
PUT  /api/settings
```

Pipeline stages live in `app/services`: parser, attachments, classifier, urgency, analysis, reply generator, risk evaluator, and `route_email_processing`.
