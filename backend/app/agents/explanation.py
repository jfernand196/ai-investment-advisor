"""Explanation agent — template first, optional LM Studio/OpenAI-compatible LLM."""

from __future__ import annotations

import time
from typing import Dict, List

from app.agents.contracts import AgentResult, EvidenceItem, ExplanationDraft, RecommendationDraft
from app.agents.context import AdvisoryContext
from app.core.config import Settings


def _template_explanation(draft: RecommendationDraft, ctx: AdvisoryContext) -> ExplanationDraft:
    feat = ctx.etf_features.get(draft.symbol, {})
    thesis = (
        f"Recomendación {draft.action} para {draft.symbol}. "
        f"Motivos: {'; '.join(draft.rationale_points)}. "
        f"Retorno 20d={feat.get('return_20d')} | vol 20d={feat.get('volatility_20d_ann')}."
    )
    risks = (
        "Riesgo de mercado, posible divergencia FX USD/COP, y para apalancados "
        "(SOXL/TQQQ) decay por volatilidad. Esto es apoyo a decisión personal, no asesoría certificada."
    )
    invalidation = (
        "Invalidar si el score combinado se revierte con fuerza o si Risk marca risk_off "
        "para altas betas / apalancados."
    )
    return ExplanationDraft(
        symbol=draft.symbol,
        thesis=thesis,
        risks=risks,
        invalidation=invalidation,
        evidence_refs=draft.evidence_refs,
        locale="es",
    )


def _try_llm_polish(text: str, settings: Settings) -> str:
    """Best-effort polish via OpenAI-compatible endpoint (LM Studio). Falls back silently."""
    try:
        from openai import OpenAI

        client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key or "local")
        response = client.chat.completions.create(
            model=settings.llm_model,
            temperature=0.2,
            max_tokens=220,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un explicador de inversiones conciso en español. "
                        "No inventes datos. No des garantías. Máximo 3 frases."
                    ),
                },
                {"role": "user", "content": text},
            ],
            timeout=8.0,
        )
        content = response.choices[0].message.content
        return content.strip() if content else text
    except Exception:
        return text


def run_explanation_agent(
    ctx: AdvisoryContext,
    compliance: AgentResult,
    settings: Settings,
    polish_with_llm: bool = True,
) -> AgentResult:
    start = time.perf_counter()
    drafts = [
        RecommendationDraft.model_validate(d) for d in compliance.payload.get("recommendations", [])
    ]
    # Explain actionable + a sample of HOLDs (all for personal universe of 9)
    explanations: List[ExplanationDraft] = []
    warnings: List[str] = []

    for draft in drafts:
        expl = _template_explanation(draft, ctx)
        if polish_with_llm and draft.action != "HOLD":
            polished = _try_llm_polish(expl.thesis, settings)
            if polished != expl.thesis:
                expl.thesis = polished
            else:
                warnings.append("llm_unavailable_template_fallback")
        explanations.append(expl)

    # dedupe warning
    warnings = sorted(set(warnings))

    return AgentResult(
        agent_name="explanation",
        confidence=0.8,
        signals=[e.model_dump() for e in explanations],
        evidence=[
            EvidenceItem(
                source="explanation",
                ref_id="explanation:v1",
                summary=f"{len(explanations)} explanations generated",
            )
        ],
        payload={"explanations": [e.model_dump() for e in explanations]},
        warnings=warnings,
        latency_ms=int((time.perf_counter() - start) * 1000),
    )
