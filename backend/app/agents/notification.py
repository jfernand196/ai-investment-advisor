"""Notification agent — builds and dispatches recommendation emails."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.agents.contracts import AgentResult, EvidenceItem
from app.core.config import Settings
from app.infrastructure.db.models import NotificationModel, RecommendationModel
from app.infrastructure.notifications.gmail import GmailEmailSender


def build_daily_email(
    run_id: int,
    recommendations: List[RecommendationModel],
    as_of: Optional[datetime] = None,
) -> Dict[str, str]:
    when = (as_of or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M UTC")
    actionable = [r for r in recommendations if r.action != "HOLD"]
    holds = [r for r in recommendations if r.action == "HOLD"]

    lines = [
        "AI Investment Advisor — Resumen diario",
        f"Run #{run_id} · {when}",
        "",
        f"Accionables: {len(actionable)} | HOLD: {len(holds)}",
        "",
    ]

    if actionable:
        lines.append("=== ACCIONES SUGERIDAS ===")
        for r in actionable:
            amount = f"${float(r.size_amount_usd or 0):,.2f}" if r.size_amount_usd else "-"
            pct = f"{float(r.size_pct or 0):.2f}%"
            lines.append(f"- {r.action} {r.symbol}: {pct} (~{amount}) conf={r.confidence}")
            if r.explanation:
                lines.append(f"  Tesis: {r.explanation.thesis}")
                lines.append(f"  Riesgos: {r.explanation.risks}")
            lines.append("")
    else:
        lines.append("No hay compras/ventas accionables hoy. Mantener asignación actual.")
        lines.append("")

    lines.append("=== HOLD (universo) ===")
    for r in holds:
        lines.append(f"- {r.symbol}: HOLD")

    lines.extend(
        [
            "",
            "Disclaimer: apoyo a decisión personal. No es asesoría financiera certificada.",
            "Detalle completo en el dashboard local (http://localhost:5173).",
        ]
    )
    text = "\n".join(lines)

    rows_html = []
    for r in recommendations:
        tone = "#3ecf8e" if r.action == "HOLD" else "#3d8bfd" if r.action in {"BUY", "INCREASE"} else "#f07178"
        thesis = (r.explanation.thesis if r.explanation else "")[:220]
        rows_html.append(
            f"<tr>"
            f"<td style='padding:8px;border-bottom:1px solid #2a3542'><b>{r.symbol}</b></td>"
            f"<td style='padding:8px;border-bottom:1px solid #2a3542;color:{tone}'>{r.action}</td>"
            f"<td style='padding:8px;border-bottom:1px solid #2a3542'>{float(r.size_pct or 0):.2f}%</td>"
            f"<td style='padding:8px;border-bottom:1px solid #2a3542;font-size:12px;color:#8b9aab'>{thesis}</td>"
            f"</tr>"
        )

    html = f"""
    <div style="font-family:IBM Plex Sans,Segoe UI,sans-serif;background:#0f1419;color:#e8eef4;padding:24px">
      <h2 style="margin:0 0 8px">AI Investment Advisor</h2>
      <p style="color:#8b9aab;margin:0 0 16px">Run #{run_id} · {when}</p>
      <p>Accionables: <b>{len(actionable)}</b> · HOLD: <b>{len(holds)}</b></p>
      <table style="width:100%;border-collapse:collapse;background:#1a222c;border-radius:12px">
        <thead>
          <tr style="color:#8b9aab;text-align:left">
            <th style="padding:8px">ETF</th><th style="padding:8px">Acción</th>
            <th style="padding:8px">Size</th><th style="padding:8px">Tesis</th>
          </tr>
        </thead>
        <tbody>{''.join(rows_html)}</tbody>
      </table>
      <p style="color:#8b9aab;font-size:12px;margin-top:16px">
        Apoyo a decisión personal. No es asesoría financiera certificada.
      </p>
    </div>
    """
    subject = f"AIA Daily · Run #{run_id} · {len(actionable)} acciones"
    return {"subject": subject, "text": text, "html": html}


def run_notification_agent(
    db: Session,
    settings: Settings,
    run_id: int,
    recommendations: List[RecommendationModel],
    as_of: Optional[datetime] = None,
) -> AgentResult:
    start = time.perf_counter()
    content = build_daily_email(run_id, recommendations, as_of=as_of)
    sender = GmailEmailSender(settings)
    send_result = sender.send(content["subject"], content["text"], content["html"])

    status = "sent" if send_result.sent else ("skipped" if send_result.skipped else "failed")
    row = NotificationModel(
        channel="email",
        status=status,
        subject=content["subject"],
        body=content["text"],
        payload={
            "run_id": run_id,
            "html_preview": True,
            "error": send_result.error,
        },
        provider_message_id=send_result.provider_message_id,
        error_message=send_result.error,
        sent_at=datetime.now(timezone.utc) if send_result.sent else None,
    )
    db.add(row)
    db.flush()

    return AgentResult(
        agent_name="notification",
        confidence=1.0 if send_result.sent else 0.5,
        signals=[{"status": status, "notification_id": row.id, "run_id": run_id}],
        evidence=[
            EvidenceItem(
                source="email",
                ref_id=f"notification:{row.id}",
                summary=f"email status={status}",
            )
        ],
        payload={
            "status": status,
            "notification_id": row.id,
            "subject": content["subject"],
            "error": send_result.error,
        },
        warnings=[send_result.error] if send_result.error else [],
        latency_ms=int((time.perf_counter() - start) * 1000),
    )
