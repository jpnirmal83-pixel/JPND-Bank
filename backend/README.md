# Jay Dee Bank Backend (FastAPI + MySQL)

## Setup

1. Create database and table:
   - Run `schema.sql` in MySQL.
2. Create `.env` from `.env.example` and fill DB credentials.
3. Install dependencies:
   - `pip install -r requirements.txt`
4. Run API:
   - `uvicorn main:app --reload --host 0.0.0.0 --port 8000`

API base URL: `http://localhost:8000/api`

## Security included

- Passwords are hashed with bcrypt (via `passlib`).
- Login returns JWT bearer token.
- Protected routes require `Authorization: Bearer <token>`.
- Admin-only routes are enforced server-side.

## Frontend integration

Frontend JS uses this API URL by default:
- `http://localhost:8000/api`

If needed, set before script load:
```html
<script>
  window.JAYDEE_API_BASE_URL = "http://localhost:8000/api";
</script>
```
