from pydantic import BaseModel


class BaselineAgentOutput(BaseModel):
    changes: list[dict]
    confidence: float
    explanation: str


class ContextAgentOutput(BaseModel):
    likely_context: list[str]
    context_confidence: float
    explanation: str


class RiskFusionOutput(BaseModel):
    state: str
    component_scores: dict[str, float]
    overall_score: float
    explanation: str


class InterventionOutput(BaseModel):
    type: str
    message: str
    rationale: str


class WellnessAgentOutput(BaseModel):
    observations: list[str]
    context_note: str | None
    recommendation: str
    sources: list[dict] = []


class AgentRunResult(BaseModel):
    employee_id: str
    date: str
    pattern: dict
    context: ContextAgentOutput
    risk: RiskFusionOutput
    intervention: InterventionOutput
    wellness: WellnessAgentOutput
