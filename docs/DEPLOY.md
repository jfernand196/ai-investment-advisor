# Deploy free — Neon + Render + Cloudflare Pages + GitHub Actions

Objetivo: que el advisory diario corra **sin tener el portátil encendido**.

## 1) Neon (Postgres free)

1. Crea cuenta en [Neon](https://neon.tech).
2. Crea proyecto `ai-investment-advisor`.
3. Copia la connection string y conviértela a SQLAlchemy/psycopg:

```text
postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require
```

> Si Neon te da `postgresql://...`, solo agrega `+psycopg` y `sslmode=require`.

## 2) Render (API free)

1. Push este repo a GitHub.
2. En Render: **New → Blueprint** (usa `render.yaml`) o Web Service Docker con root `backend`.
3. Variables obligatorias:

| Key | Valor |
|---|---|
| `DATABASE_URL` | connection string Neon (`postgresql+psycopg://...?sslmode=require`) |
| `APP_API_KEY` | string largo aleatorio |
| `CORS_ORIGINS` | URL de Cloudflare Pages, ej. `https://ai-investment-advisor.pages.dev` |
| `SMTP_USERNAME` | tu Gmail |
| `SMTP_PASSWORD` | App Password de Google |
| `EMAIL_FROM` / `EMAIL_TO` | tu Gmail |
| `FRED_API_KEY` | opcional (gratis) |

4. Health check: `/api/v1/health/live`
5. Tras el primer deploy, prueba:

```bash
curl https://YOUR-API.onrender.com/api/v1/health/live
curl -H "X-API-Key: YOUR_KEY" https://YOUR-API.onrender.com/api/v1/meta/config
```

## 3) Cloudflare Pages (frontend free)

1. Cloudflare → Pages → Connect GitHub repo.
2. Build settings:

| Campo | Valor |
|---|---|
| Root directory | `frontend` |
| Build command | `npm ci && npm run build` |
| Build output | `dist` |

3. Environment variables (Production):

| Key | Valor |
|---|---|
| `VITE_API_URL` | `https://YOUR-API.onrender.com` |
| `VITE_API_KEY` | el mismo `APP_API_KEY` |

4. Redeploy después de setear env vars.

> Nota de seguridad personal: la API key queda en el bundle del frontend. Es suficiente para uso personal obscuro; no compartas la URL públicamente. Rota la key si se filtra.

## 4) GitHub Actions (cron diario)

En el repo → Settings → Secrets and variables → Actions:

| Secret | Valor |
|---|---|
| `ADVISORY_API_URL` | `https://YOUR-API.onrender.com` |
| `ADVISORY_API_KEY` | mismo `APP_API_KEY` |

Workflow: `.github/workflows/daily-advisory.yml`

- Corre lun–vie 12:00 UTC (~7:00 Colombia)
- Despierta Render, ingesta mercado, corre advisory + email
- También se puede lanzar manualmente (Actions → Daily Advisory → Run workflow)

## 5) LLM en la nube (opcional)

En Render free no corre LM Studio. El Explanation Agent ya tiene fallback a template si el LLM no responde.

Si quieres polish con free tier:

- Gemini / Groq keys en Render (`LLM_*`) — se puede cablear después sin tocar el grafo.

## Checklist final

- [ ] Neon DB conectada
- [ ] Render health `ok`
- [ ] Cloudflare dashboard carga recomendaciones
- [ ] Secretos GitHub configurados
- [ ] Dry-run manual del workflow Daily Advisory
- [ ] Email Gmail App Password válido
