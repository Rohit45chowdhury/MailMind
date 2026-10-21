# MailMind AI

Your Inbox, Intelligently Managed. React + Vite + Tailwind frontend for the existing FastAPI / LangGraph / Groq backend.

## Run it
```bash
npm install
cp .env.example .env     # VITE_API_URL=http://127.0.0.1:8000
npm run dev              # http://localhost:5173
```
Start the backend separately (for example `uvicorn main:app --reload`).

## CORS (backend)
Add this to your FastAPI app:
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## How each page maps to the backend
All calls go through `src/api/axios.js` (base URL from `VITE_API_URL`).

| Page | Route | Endpoint | Fields read from the response |
|---|---|---|---|
| Spam Detection | `/spam` | `POST /spam` | `verdict`, `is_spam`, `confidence`, `reason` |
| Email Summarizer | `/summarize` | `POST /summarize` | `summary` (may be null), `is_spam`, `spam_reason` or `reason` |
| Email Generator | `/generate` | `POST /generate` | `subject`, `body` |
| Grammar Checker | `/grammar` | `POST /grammar-check` | `original_text`, `corrected_text`, `has_errors`, `issue_count`, `issues[]` |
| Send Email | `/send` | `POST /send` | `message` (optional) |

If your backend uses different response field names, adjust them in the matching page file.

## Notes
- A loading page shows on first load (`SplashScreen.jsx`); pages are lazy-loaded with a spinner fallback.
- Dashboard statistics are **sample data**, labeled as such. Recent activity lists real results from the current session only; there is no history endpoint.
- Sending always requires the confirmation dialog. AI output is never sent automatically.
- Light theme by default; dark mode is saved in the browser.
