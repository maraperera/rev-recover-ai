from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from src.agents.nodes.auditor import audit_reconciliation_node
from src.agents.nodes.erp_matcher import fetch_sap_po_node
from src.agents.nodes.extractor import extract_invoice_node
from src.agents.nodes.policy_rag import retrieve_contract_clauses_node
from src.agents.state import AgentAuditState


def should_interrupt_for_review(state: AgentAuditState) -> str:
    report = state.get("audit_report")
    if report and report.total_recoverable > 0:
        return "human_review"
    return "execute_recovery"


async def human_review_node(state: AgentAuditState) -> dict:
    """Pass-through node representing human evaluation in the loop."""
    return {}


async def execute_recovery_node(state: AgentAuditState) -> dict:
    """Applies credit memo or marks invoice flagged in ERP upon approval."""
    verdict = state.get("human_verdict")
    if verdict == "APPROVED":
        return {"recovery_executed": True}
    return {"recovery_executed": False}


# In-memory checkpointer with native async support
checkpointer = MemorySaver()

builder = StateGraph(AgentAuditState)

# Add processing nodes
builder.add_node("extractor", extract_invoice_node)
builder.add_node("policy_rag", retrieve_contract_clauses_node)
builder.add_node("sap_matcher", fetch_sap_po_node)
builder.add_node("auditor", audit_reconciliation_node)
builder.add_node("human_review", human_review_node)
builder.add_node("execute_recovery", execute_recovery_node)

# Define edges
builder.set_entry_point("extractor")
builder.add_edge("extractor", "policy_rag")
builder.add_edge("policy_rag", "sap_matcher")
builder.add_edge("sap_matcher", "auditor")

builder.add_conditional_edges(
    "auditor",
    should_interrupt_for_review,
    {
        "human_review": "human_review",
        "execute_recovery": "execute_recovery",
    },
)

builder.add_edge("human_review", "execute_recovery")
builder.add_edge("execute_recovery", END)

# Compile graph with human review interrupt hook
audit_graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["human_review"],
)