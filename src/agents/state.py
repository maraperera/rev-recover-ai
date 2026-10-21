from typing import Annotated, Any, Dict, List, Literal, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class InvoiceLineItem(BaseModel):
    item_id: str = Field(..., description="Line item ID or number")
    description: str = Field(..., description="Description of good or service")
    quantity: float = Field(..., description="Billed quantity")
    unit_price: float = Field(..., description="Price charged per unit")
    net_amount: float = Field(..., description="Line total excluding tax")
    po_item_ref: Optional[str] = Field(None, description="Matched SAP PO line item reference")


class InvoicePayload(BaseModel):
    invoice_id: str
    supplier_id: str
    supplier_name: str
    po_number: str
    currency: str = "USD"
    invoice_date: str
    gross_amount: float
    line_items: List[InvoiceLineItem]


class Discrepancy(BaseModel):
    item_id: str
    discrepancy_type: Literal[
        "UNIT_PRICE_VARIANCE",
        "QUANTITY_OVERBILL",
        "UNCLAIMED_DISCOUNT",
        "CONTRACT_RATE_VIOLATION",
    ]
    billed_amount: float
    entitled_amount: float
    recoverable_amount: float
    explanation: str
    clause_reference: str


class DiscrepancyReport(BaseModel):
    invoice_id: str
    po_number: str
    supplier_id: str
    total_recoverable: float
    discrepancies: List[Discrepancy]
    dispute_memo: str
    status: Literal["NEEDS_HUMAN_REVIEW", "APPROVED", "REJECTED"] = "NEEDS_HUMAN_REVIEW"


class AgentAuditState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    raw_document_text: str
    extracted_invoice: Optional[InvoicePayload]
    contract_clauses: List[Dict[str, Any]]
    sap_po_data: Optional[Dict[str, Any]]
    audit_report: Optional[DiscrepancyReport]
    human_verdict: Optional[Literal["APPROVED", "REJECTED"]]
    recovery_executed: bool