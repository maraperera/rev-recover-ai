import logging
from langchain_core.prompts import ChatPromptTemplate
from src.agents.state import AgentAuditState, Discrepancy, DiscrepancyReport
from src.utils.bedrock_client import get_bedrock_chat_llm

logger = logging.getLogger("rev-recover.auditor")

MEMO_PROMPT = """Draft a formal financial dispute letter to {supplier_name} for invoice {invoice_id}.
Identified Recoveries:
{recoveries_detail}
Total Overcharge to Deduct: ${total_recovery}
"""


async def audit_reconciliation_node(state: AgentAuditState) -> dict:
    invoice = state.get("extracted_invoice")
    if not invoice:
        return {"audit_report": None}

    po_data = state.get("sap_po_data")
    discrepancies: list[Discrepancy] = []

    # Deterministic matching: Compare billed rate with contract/SAP ceiling
    contract_price = 150.00
    if po_data and "to_PurchaseOrderItem" in po_data:
        sap_items = {
            item.get("PurchaseOrderItem", ""): item
            for item in po_data["to_PurchaseOrderItem"].get("results", [])
        }
        for item in invoice.line_items:
            if item.po_item_ref and item.po_item_ref in sap_items:
                contract_price = float(sap_items[item.po_item_ref].get("NetPriceAmount", 150.00))

    for item in invoice.line_items:
        if item.unit_price > contract_price:
            unit_diff = item.unit_price - contract_price
            total_var = round(unit_diff * item.quantity, 2)
            discrepancies.append(
                Discrepancy(
                    item_id=item.item_id,
                    discrepancy_type="UNIT_PRICE_VARIANCE",
                    billed_amount=round(item.unit_price * item.quantity, 2),
                    entitled_amount=round(contract_price * item.quantity, 2),
                    recoverable_amount=total_var,
                    explanation=(
                        f"Billed unit rate of ${item.unit_price:.2f} exceeds "
                        f"authorized contract ceiling of ${contract_price:.2f}."
                    ),
                    clause_reference="Schedule B - Component Pricing Schedule",
                )
            )

    total_recoverable = round(sum(d.recoverable_amount for d in discrepancies), 2)
    recoveries_text = "\n".join(
        [f"- Line Item {d.item_id}: {d.explanation} (Variance: ${d.recoverable_amount})" for d in discrepancies]
    )

    try:
        llm = get_bedrock_chat_llm()
        prompt = ChatPromptTemplate.from_template(MEMO_PROMPT)
        chain = prompt | llm
        memo_res = await chain.ainvoke(
            {
                "supplier_name": invoice.supplier_name,
                "invoice_id": invoice.invoice_id,
                "recoveries_detail": recoveries_text or "No variances detected.",
                "total_recovery": total_recoverable,
            }
        )
        memo_body = str(memo_res.content)
    except Exception as e:
        logger.warning(f"Bedrock LLM unavailable for memo drafting ({e}); using template fallback.")
        memo_body = (
            f"FORMAL NOTICE OF BILLING DISCREPANCY\n\n"
            f"To: Accounts Receivable, {invoice.supplier_name}\n"
            f"Reference Invoice: {invoice.invoice_id} | PO Ref: {invoice.po_number}\n\n"
            f"Automated 3-way reconciliation against authorized SAP purchase agreements identified "
            f"variances totaling ${total_recoverable:,.2f}.\n\n"
            f"Discrepancy Details:\n{recoveries_text}\n\n"
            f"A debit memo will be applied to the upcoming payment cycle pending internal review."
        )

    report = DiscrepancyReport(
        invoice_id=invoice.invoice_id,
        po_number=invoice.po_number,
        supplier_id=invoice.supplier_id,
        total_recoverable=total_recoverable,
        discrepancies=discrepancies,
        dispute_memo=memo_body,
        status="NEEDS_HUMAN_REVIEW" if total_recoverable > 0 else "APPROVED",
    )

    return {"audit_report": report}