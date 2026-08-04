"""CLI: python -m app.jobs.run_advisory [--no-email]"""

from __future__ import annotations

import argparse
import json

from app.application.advisory.run import execute_advisory_run
from app.core.config import get_settings
from app.infrastructure.db.session import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Run multi-agent advisory pipeline")
    parser.add_argument("--no-email", action="store_true", help="Skip Gmail notification")
    args = parser.parse_args()

    settings = get_settings()
    db = SessionLocal()
    try:
        result = execute_advisory_run(
            db,
            settings,
            trigger="on_demand",
            notify_email=False if args.no_email else None,
        )
        print(
            json.dumps(
                {
                    "run_id": result.run_id,
                    "status": result.status,
                    "recommendations_count": result.recommendations_count,
                    "actionable_count": result.actionable_count,
                    "warnings": result.warnings,
                    "email_status": result.email_status,
                    "notification_id": result.notification_id,
                    "error_message": result.error_message,
                },
                indent=2,
            )
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
