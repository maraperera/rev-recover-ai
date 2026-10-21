from langchain_core.prompts import ChatPromptTemplate
from src.agents.state import AgentAuditState, Discrepancy, DiscrepancyReport
from src.utils.bedrock_client import get_bedrock_chat_llm

MEMO_PROMPT = """Draft a formal, concise financial dispute letter to {supplier_name} for invoice {invoice_id}.
Identified Recoveries:
{recoveries_detail}
Total Overcharge to Deduct: ${total_recovery}
"""


async def audit_reconciliation_node(state: AgentAuditState) -> dict:
    invoice = state["extracted_invoice"]
    po_data = state.get("sap_po_data")
    clauses = state.get("contract_clauses", [])

    discrepancies: list[Discrepancy] = []

    # Deterministic matching against SAP PO items
    if po_data and "to_PurchaseOrderItem" in po_data:
        sap_items = {
            item["PurchaseOrderItem"]: item
            for item in po_data["to_PurchaseOrderItem"].get("results", [])
        }

        for item in invoice.line_items:
            sap_item = sap_items.get(item.po_item_ref or item.item_id)
            if sap_item:
                contract_price = float(sap_item.get("NetPriceAmount", 0.0))
                # Detect rate variance
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
                                f"Billed rate ${item.unit_price} exceeds agreed SAP "
                                f"Purchase Order rate ${contract_price}."
                            ),
                            clause_reference="SAP S/4HANA PO Item Rate Ceiling",
                        )
                    )

    total_recoverable = round(sum(d.recoverable_amount for d in discrepancies), 2)

    # Bedrock Claude drafts formal audit memo
    llm = get_bedrock_chat_llm()
    recoveries_text = "\n".join(
        [f"- Item {d.item_id}: {d.explanation} (${d.recoverable_amount})" for d in discrepancies]
    )

    memo_prompt = ChatPromptTemplate.from_template(MEMO_PROMPT)
    memo_chain = memo_prompt | llm
    memo_res = await memo_chain.ainvoke(
        {
            "supplier_name": invoice.supplier_name,
            "invoice_id": invoice.invoice_id,
            "recoveries_detail": recoveries_text or "No variances detected.",
            "total_recovery": total_recoverable,
        }
    )

    report = DiscrepancyReport(
        invoice_id=invoice.invoice_id,
        po_number=invoice.po_number,
        supplier_id=invoice.supplier_id,
        total_recoverable=total_recoverable,
        discrepancies=discrepancies,
        dispute_memo=str(memo_res.content),
        status="NEEDS_HUMAN_REVIEW" if total_recoverable > 0 else "APPROVED",
    )

    return {"audit_report": report}