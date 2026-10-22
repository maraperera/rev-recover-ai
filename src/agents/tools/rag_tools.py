import logging
from typing import Any, Dict, List

logger = logging.getLogger("rev-recover.rag_tools")

# Contract knowledge base fallback
CONTRACT_DATABASE = [
    {
        "supplier_id": "1000042",
        "section": "Schedule B - Component Pricing Schedule",
        "source_file": "MSA_GlobalIndustrialSolutions_2024.pdf",
        "clause_text": (
            "Section 4.2 - Rate Caps: Heavy Duty Industrial Ball Bearings (Item #00010) "
            "are contracted at a maximum price ceiling of $150.00 USD per unit. Any billing "
            "exceeding this unit ceiling shall be subject to immediate debit memo deduction."
        ),
    },
    {
        "supplier_id": "1000042",
        "section": "Clause 8.1 - Volume Rebates",
        "source_file": "MSA_GlobalIndustrialSolutions_2024.pdf",
        "clause_text": (
            "Orders exceeding 40 units per purchase order are entitled to an additional "
            "2% prompt-payment recovery discount if settled within 30 days."
        ),
    },
]


class ContractClauseRAG:
    def __init__(self) -> None:
        self.vector_store = None
        self._init_store()

    def _init_store(self) -> None:
        try:
            from config.settings import settings
            from langchain_community.vectorstores import Chroma
            from src.utils.bedrock_client import get_bedrock_embeddings

            self.vector_store = Chroma(
                collection_name="vendor_contracts",
                embedding_function=get_bedrock_embeddings(),
                persist_directory=settings.CHROMA_PERSIST_DIRECTORY,
            )
        except Exception as e:
            logger.warning(f"Vector store initialization deferred: {e}")
            self.vector_store = None

    def search_applicable_clauses(
        self, supplier_id: str, query: str, top_k: int = 3
    ) -> List[Dict[str, Any]]:
        # Attempt vector search only if store and AWS Titan embeddings work
        if self.vector_store:
            try:
                results = self.vector_store.similarity_search(
                    query=query,
                    k=top_k,
                    filter={"supplier_id": supplier_id} if supplier_id else None,
                )
                if results:
                    return [
                        {
                            "clause_text": doc.page_content,
                            "section": doc.metadata.get("section", "General Terms"),
                            "source_file": doc.metadata.get("source", "Contract Store"),
                        }
                        for doc in results
                    ]
            except Exception as exc:
                logger.warning(f"Embedding search failed ({exc}). Using contract repository fallback.")

        # Deterministic fallback matched by supplier_id
        matched = [c for c in CONTRACT_DATABASE if c["supplier_id"] == supplier_id]
        return matched if matched else CONTRACT_DATABASE[:top_k]