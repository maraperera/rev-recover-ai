from src.agents.state import AgentAuditState
from src.agents.tools.rag_tools import ContractClauseRAG

rag_engine = ContractClauseRAG()


async def retrieve_contract_clauses_node(state: AgentAuditState) -> dict:
    invoice = state["extracted_invoice"]
    if not invoice:
        return {"contract_clauses": []}

    query = f"Pricing terms, unit rates, and prompt discounts for supplier {invoice.supplier_id}"
    clauses = rag_engine.search_applicable_clauses(
        supplier_id=invoice.supplier_id, query=query, top_k=4
    )
    return {"contract_clauses": clauses}