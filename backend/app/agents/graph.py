"""LangGraph orchestrator — research fan-out then risk → strategy → compliance → explanation."""

from __future__ import annotations

from typing import Any, Dict, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.compliance import run_compliance_agent
from app.agents.contracts import AgentResult
from app.agents.context import AdvisoryContext
from app.agents.explanation import run_explanation_agent
from app.agents.research import run_all_research
from app.agents.risk import run_risk_agent
from app.agents.strategy import run_strategy_agent
from app.core.config import Settings


class AdvisoryState(TypedDict, total=False):
    context: AdvisoryContext
    settings: Settings
    research: Dict[str, AgentResult]
    risk: AgentResult
    strategy: AgentResult
    compliance: AgentResult
    explanation: AgentResult
    error: str


def _research_node(state: AdvisoryState) -> Dict[str, Any]:
    ctx = state["context"]
    return {"research": run_all_research(ctx)}


def _risk_node(state: AdvisoryState) -> Dict[str, Any]:
    return {"risk": run_risk_agent(state["context"], state["research"])}


def _strategy_node(state: AdvisoryState) -> Dict[str, Any]:
    return {"strategy": run_strategy_agent(state["context"], state["research"], state["risk"])}


def _compliance_node(state: AdvisoryState) -> Dict[str, Any]:
    return {"compliance": run_compliance_agent(state["context"], state["strategy"], state["risk"])}


def _explanation_node(state: AdvisoryState) -> Dict[str, Any]:
    return {
        "explanation": run_explanation_agent(
            state["context"],
            state["compliance"],
            state["settings"],
            polish_with_llm=True,
        )
    }


def build_advisory_graph():
    graph = StateGraph(AdvisoryState)
    graph.add_node("research", _research_node)
    graph.add_node("risk", _risk_node)
    graph.add_node("strategy", _strategy_node)
    graph.add_node("compliance", _compliance_node)
    graph.add_node("explanation", _explanation_node)

    graph.add_edge(START, "research")
    graph.add_edge("research", "risk")
    graph.add_edge("risk", "strategy")
    graph.add_edge("strategy", "compliance")
    graph.add_edge("compliance", "explanation")
    graph.add_edge("explanation", END)
    return graph.compile()


ADVISORY_GRAPH = build_advisory_graph()
