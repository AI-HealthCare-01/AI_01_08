# Frontend (React + Vite)

## Run

```bash
cd frontend
npm install
npm run dev
```

Default URL: `http://localhost:5173`

## API Target

By default frontend calls backend at `http://localhost:8001`.

If needed, create `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8001
```

## Team Workflow

- Backend API code: `app/`
- Frontend UI code: `frontend/`
- Contract endpoint used by dashboard: `GET /api/v1/healthcare/summary`
- Signup endpoint used by UI: `POST /api/v1/auth/signup`
