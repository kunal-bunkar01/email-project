# Sable

Sable is a local AI email assistant. It reads a Gmail inbox, classifies each message, judges urgency, drafts a reply, checks that reply for risk, and either sends it or holds it for you.

You can run the whole product on your machine with SQLite. Demo mode needs no Gmail account and no LLM key.

## Requirements

- Python 3.11+
- Node.js 18+
- npm

No Docker, Redis, PostgreSQL, or other services.

## Demo mode, the fast path

Demo mode is the default. It loads a sample inbox and simulates classification, replies, and sending. Nothing leaves your computer.

```bash
npm run setup
npm run dev
```

Then open:

- App: http://localhost:5173
- API docs: http://localhost:8000/docs

`npm run setup` creates `backend/venv`, installs Python packages, and installs the frontend. `npm run dev` starts both servers.

If you prefer to install by hand, use the steps below. They do the same thing.

## Install by hand

### Backend

```bash
cd backend
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
pip install -r requirements.txt
```

macOS and Linux:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

### Root helper

From the project root, `npm install` installs the small process runner used by `npm run dev`. The frontend packages are installed by `npm run setup`, or by `npm install` inside `frontend`.

## Environment

Configuration lives in `backend/.env`. Copy the example if you want to change defaults:

```bash
cd backend
copy .env.example .env
```

On macOS or Linux, use `cp .env.example .env`.

| Variable | Purpose |
| --- | --- |
| `DEMO_MODE` | `true` uses the sample inbox and a local AI stand-in. `false` uses Gmail and OpenAI. |
| `GOOGLE_CLIENT_ID` | OAuth client id |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret |
| `GOOGLE_REDIRECT_URI` | Must be `http://localhost:8000/api/auth/google/callback` |
| `OPENAI_API_KEY` | Used only when demo mode is off |
| `OPENAI_MODEL` | Defaults to `gpt-4o-mini` |
| `EMAIL_POLL_ENABLED` | Initial on/off value for background polling |
| `EMAIL_POLL_INTERVAL` | Initial poll interval in seconds |
| `GMAIL_SYNC_LIMIT` | How many recent messages to pull |
| `FRONTEND_URL` | Where OAuth sends you afterwards |
| `DATABASE_URL` | Optional. Blank uses `backend/data/email_assistant.db` |

The frontend can stay with an empty `frontend/.env`. Vite proxies `/api` to the backend.

If `DEMO_MODE=true`, the app ignores missing keys and still starts. If demo mode is off and `OPENAI_API_KEY` is empty, the app still starts and shows **AI provider not configured**.

## Run

Backend, from `backend` with the virtualenv active:

```bash
uvicorn app.main:app --reload
```

Frontend, from `frontend`:

```bash
npm run dev
```

Or both from the project root:

```bash
npm run dev
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

The database file is created automatically at `backend/data/email_assistant.db` the first time the backend starts.

## What you can do in demo mode

1. Open the dashboard and look at the sample mail.
2. Open **Review queue**, edit a draft, and choose **Edit & Send**, **Approve & Send**, **Reject**, or **Regenerate**.
3. Open an unprocessed email and choose **Process**. A routine note can be auto-sent. A payment request stays in review.
4. Change tone, signature, and auto-send thresholds in **Settings**.

Sending in demo mode only updates the local database.

## Gmail setup

Do this when you want a real inbox. Keep `DEMO_MODE=true` until the credentials work, then set it to `false` and restart the backend.

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project.
3. Enable the **Gmail API** for that project.
4. Configure the OAuth consent screen.
   - User type: External is fine for a personal project.
   - Add your Gmail address as a test user while the app is in testing.
5. Create an OAuth client.
   - Type: **Web application**
   - Authorized redirect URI: `http://localhost:8000/api/auth/google/callback`
6. Copy the client id and client secret into `backend/.env`:

```env
DEMO_MODE=false
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
```

You can instead download the client JSON and save it as:

```text
backend/credentials/client_secret.json
```

The backend reads that file when the environment variables are empty. Do not commit it.

Scopes used:

- Read mail and threads
- Send mail
- Read your email address and name

In the app, open **Settings** and choose **Connect Gmail**. After Google sends you back, use **Sync Gmail** on the dashboard. New messages are saved, parsed, and run through the assistant. With auto-send on, only low-risk, high-confidence replies go out. Everything else waits in Review.

Background polling is optional. Turn it on under Settings → Processing, or set `EMAIL_POLL_ENABLED=true`. The app works with polling off. Sync still runs when you click the button. Polling uses a normal Python background task. It does not need Redis or Celery.

## Free AI model

OpenAI's own API is paid. This project can use Groq's free tier instead. Groq serves open models through the same style of API, with a daily request limit and no charge on the free plan.

1. Open [console.groq.com/keys](https://console.groq.com/keys) and create a free API key.
2. In `backend/.env` set:

```env
DEMO_MODE=false
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_free_key
GROQ_MODEL=llama-3.3-70b-versatile
```

3. Restart the backend.

A lighter free model, if you hit the daily limit, is `llama-3.1-8b-instant`. Google AI Studio is another free option: set `LLM_PROVIDER=gemini` and `GEMINI_API_KEY`. Paid OpenAI still works with `LLM_PROVIDER=openai` and `OPENAI_API_KEY`.

Each email makes a few model calls, so a large sync can reach the free daily cap. When that happens the email stays unprocessed and nothing is sent.

The pipeline talks to an `AIProvider` interface. Demo mode, Groq, Gemini, and OpenAI all use that same path.

## How a message moves

```text
Parse → clean → attachments → thread context
  → classify → urgency → analysis → reply → risk → routing
  → auto send, or human review
```

Routing defaults:

- Auto-send off: every reply waits for you
- High risk, or risk above your maximum: review
- High urgency: review
- Confidence below your minimum (default 80%): review
- Newsletters, promotions, and spam: no reply
- Otherwise: auto send

You can change the thresholds in Settings.

## Project map

```text
backend/app/api/routes     HTTP endpoints
backend/app/db             SQLite models
backend/app/services       Gmail, parsing, and each AI stage
backend/app/workers        Optional inbox polling
frontend/src/pages         Dashboard, inbox, review, settings
```

## Tests

From `backend`, with the virtualenv active:

```bash
pytest
```

## Troubleshooting

- **Port already in use.** Stop the other process on 5173 or 8000, then start again.
- **pip says a file is in use.** This project lives in a folder Windows may be syncing. Run `npm run setup` again. The second install usually finishes.
- **`npm run dev` cannot find Python.** Run `npm run setup` first.
- **Google redirect mismatch.** The redirect URI in Cloud Console must match `GOOGLE_REDIRECT_URI` exactly.
- **Access blocked.** Add your Gmail address as a test user on the OAuth consent screen.
- **AI provider not configured.** Add `OPENAI_API_KEY`, or set `DEMO_MODE=true`.
- **OCR.** Image text extraction uses Tesseract only if it is already installed. Missing OCR does not stop the app. PDF text uses PyMuPDF.
