# AI Investment Advisor

Asesor de inversión personal (1 usuario) basado en multi-agentes.  
Stack económico: FastAPI + Postgres + Vite/React + Render + Gmail + Neon.

## Estado

**P0.6 — Deploy free ready**

- Backend FastAPI + Clean Architecture + LangGraph multi-agente
- Frontend Vite/React dashboard (recomendaciones, FX, email preview)
- Postgres local (Docker `:5433`) / Neon en prod
- Ingesta yfinance (ETFs, USD/COP, DXY) + FRED opcional
- Email Gmail + Notification Agent
- `X-API-Key` para proteger API pública
- `render.yaml`, Cloudflare Pages, GitHub Actions CI + cron diario

Guía paso a paso: [docs/DEPLOY.md](docs/DEPLOY.md)

## Setup local

```bash
cp .env.example .env
docker compose up -d db

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# otra terminal
cd frontend
npm install
npm run dev
```

- API: http://localhost:8000/docs  
- UI: http://localhost:5173  

## Universo ETF

| Bucket | % | ETFs |
|---|---|---|
| Conservador | 40% | VOO, VTI, SCHD |
| Moderado | 40% | QQQ, VGT, VXUS |
| Agresivo | 20% | SMH, SOXL, TQQQ |

Caps: SMH ≤10%, SOXL ≤5%, TQQQ ≤5%.

## Comandos útiles

```bash
# Market ingest
cd backend && python -m app.jobs.ingest_market --lookback-days 365

# Advisory (+ email si SMTP configurado)
python -m app.jobs.run_advisory
```

## Deploy free (resumen)

| Pieza | Servicio | Artefacto |
|---|---|---|
| DB | Neon | `DATABASE_URL=postgresql+psycopg://...?sslmode=require` |
| API | Render | `render.yaml` + `backend/Dockerfile` |
| UI | Cloudflare Pages | `frontend/` → `dist` |
| Cron | GitHub Actions | `.github/workflows/daily-advisory.yml` |
| Email | Gmail App Password | `SMTP_*` |

Secrets GitHub Actions: `ADVISORY_API_URL`, `ADVISORY_API_KEY`.

## Próximo paso

Publicar el repo en GitHub y completar el checklist de [docs/DEPLOY.md](docs/DEPLOY.md) (Neon → Render → Pages → Secrets → dry-run del cron).
