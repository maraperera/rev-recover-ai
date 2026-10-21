from src.agents.state import AgentAuditState
from src.integrations.sap_client import SAPClient

sap_client = SAPClient()


async def fetch_sap_po_node(state: AgentAuditState) -> dict:
    invoice = state["extracted_invoice"]
    if not invoice or not invoice.po_number:
        return {"sap_po_data": None}

    po_data = await sap_client.get_purchase_order(invoice.po_number)
    return {"sap_po_data": po_data}