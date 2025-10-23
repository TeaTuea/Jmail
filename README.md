# Jmail

Jmail is a self-contained Python WSGI application that provides account creation, login, and authenticated email sending through a configurable SMTP relay. It is designed for simple deployments (Render, Fly.io, Railway, VPS, etc.) and can be embedded inside Google Sites with the included static frontend.

## Features

- Zero third-party dependencies; everything is implemented with the Python standard library.
- User registration and login with salted PBKDF2 password hashing and signed session tokens.
- Authenticated email sending through any SMTP provider (Gmail, Outlook, Mailgun, etc.).
- Lightweight REST-style API plus a ready-to-embed HTML/CSS/JS frontend.
- Health check endpoint for monitoring.

## Project layout

```
app.py                 # WSGI server entry point
frontend/              # Static files for embedding
jmail/                 # Core application package
tests/                 # pytest suite
```

## Getting started

### 1. Configure the environment

Create a `.env` file or export variables directly. Only the SMTP settings and JWT secret are required for production use.

```bash
export DATABASE_PATH=jmail.db
export JWT_SECRET="super-secret-key"
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT=587
export SMTP_USERNAME="your-email@example.com"
export SMTP_PASSWORD="your-app-password"
export SMTP_FROM_NAME="Jmail"
export SMTP_FROM_EMAIL="your-email@example.com"
```

### 2. Run the server

```bash
python app.py
```

The API will be available at `http://localhost:8000/api`.

### 3. API overview

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/health` | GET | Returns `{ "status": "ok" }` |
| `/api/register` | POST | Create a new user and receive a signed token |
| `/api/login` | POST | Authenticate and receive a signed token |
| `/api/profile` | GET | Return the authenticated user's profile |
| `/api/send` | POST | Send an email via the configured SMTP relay |

#### Example requests

```bash
curl -X POST http://localhost:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"p@55word","display_name":"Alice"}'
```

```bash
curl -X POST http://localhost:8000/api/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"to":"friend@example.com","subject":"Hi","body":"Hello from Jmail!"}'
```

### 4. Embedding on Google Sites

1. Deploy the Python app and note its public base URL (e.g. `https://your-jmail-app.fly.dev`).
2. Host the `frontend/` files on any static host or embed the HTML directly into Google Sites (`Insert > Embed > Embed Code`).
3. If the frontend is hosted separately, define `window.API_BASE` before loading `script.js`:

   ```html
   <script>
     window.API_BASE = "https://your-jmail-app.fly.dev/api";
   </script>
   <script src="https://your-static-site/script.js" defer></script>
   ```

4. The provided frontend performs registration, login, and email sending against the REST API using fetch.

### 5. Running tests

```bash
pytest
```

## Security notes

- Passwords are hashed using `hashlib.pbkdf2_hmac` with a random 128-bit salt and 120k iterations.
- Session tokens use HMAC-SHA256 and include issued-at plus expiration timestamps (default 1 hour).
- All users share the SMTP credentials configured on the server. Extend `jmail/database.py` if you need per-user SMTP accounts.
- Always deploy behind HTTPS to protect credentials in transit.
