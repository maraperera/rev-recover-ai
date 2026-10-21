import uuid
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.agents.graph import audit_graph

router = APIRouter()


class AuditRequest(BaseModel):
    raw_document_text: str


class AuditApprovalRequest(BaseModel):
    thread_id: str
    verdict: Literal["APPROVED", "REJECTED"]


@router.post("/trigger")
async def trigger_invoice_audit(payload: AuditRequest):
    """Initiates an invoice audit.

    Runs until completion or pauses at HITL interrupt.
    """
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "messages": [],
        "raw_document_text": payload.raw_document_text,
        "extracted_invoice": None,
        "contract_clauses": [],
        "sap_po_data": None,
        "audit_report": None,
        "human_verdict": None,
        "recovery_executed": False,
    }

    # Execute graph until interrupt
    result = await audit_graph.ainvoke(initial_state, config=config)
    report = result.get("audit_report")

    return {
        "thread_id": thread_id,
        "status": "NEEDS_APPROVAL" if report and report.total_recoverable > 0 else "COMPLETED",
        "audit_report": report,
    }


@router.get("/status/{thread_id}")
async def get_audit_status(thread_id: str):
    """Retrieves current checkpoint state for a given audit thread."""
    config = {"configurable": {"thread_id": thread_id}}
    state = await audit_graph.aget_state(config)
    if not state or not state.values:
        raise HTTPException(status_code=404, detail="Audit thread not found")
    return {"thread_id": thread_id, "state": state.values, "next_step": state.next}


@router.post("/review")
async def submit_human_review(payload: AuditApprovalRequest):
    """Resumes the interrupted workflow with approval or rejection."""
    config = {"configurable": {"thread_id": payload.thread_id}}
    current_state = await audit_graph.aget_state(config)

    if not current_state.next:
        raise HTTPException(status_code=400, detail="Thread is not waiting for human review")

    # Update state with reviewer verdict and resume
    await audit_graph.aupdate_state(
        config, {"human_verdict": payload.verdict}, as_node="human_review"
    )
    result = await audit_graph.ainvoke(None, config=config)

    return {
        "thread_id": payload.thread_id,
        "status": "COMPLETED",
        "recovery_executed": result.get("recovery_executed", False),
    }