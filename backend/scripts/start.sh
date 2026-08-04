#!/sh
set -eu

echo "Running migrations..."
alembic upgrade head

echo "Seeding reference data (idempotent)..."
python - <<'PY'
from app.core.config import get_settings
from app.infrastructure.db.seed import seed_reference_data
from app.infrastructure.db.session import SessionLocal

db = SessionLocal()
try:
    print(seed_reference_data(db, get_settings()))
finally:
    db.close()
PY

PORT="${PORT:-8000}"
echo "Starting API on :$PORT"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
