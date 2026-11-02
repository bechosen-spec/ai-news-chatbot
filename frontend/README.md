# Frontend integration (Phase 2)

The planned client is React + TypeScript + Tailwind CSS, deployed on Vercel. Phase 1 intentionally
contains no production UI. Configure `VITE_API_BASE_URL` with the deployed FastAPI origin and keep
all API calls in typed service modules. Authentication will require a provider decision, secure
token storage, backend authorization, and separate user/admin permissions before implementation.

Local development will use `http://localhost:8000`; production CORS must list the exact Vercel
origin. The generated OpenAPI schema at `/openapi.json` is the source of truth for client types.

