from typing import Any, Dict, List
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from config.settings import settings
from src.utils.bedrock_client import get_bedrock_embeddings


class ContractClauseRAG:
    def __init__(self) -> None:
        self.embeddings = get_bedrock_embeddings()
        self.vector_store = Chroma(
            collection_name="vendor_contracts",
            embedding_function=self.embeddings,
            persist_directory=settings.CHROMA_PERSIST_DIRECTORY,
        )

    def ingest_contract_documents(self, documents: List[Document]) -> None:
        """Indexes vendor Master Service Agreements (MSAs) into ChromaDB."""
        self.vector_store.add_documents(documents)

    def search_applicable_clauses(
        self, supplier_id: str, query: str, top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Dense similarity retrieval with metadata pre-filtering by supplier."""
        results = self.vector_store.similarity_search(
            query=query,
            k=top_k,
            filter={"supplier_id": supplier_id} if supplier_id else None,
        )
        return [
            {
                "clause_text": doc.page_content,
                "section": doc.metadata.get("section", "General Terms"),
                "source_file": doc.metadata.get("source", "Unknown Contract"),
            }
            for doc in results
        ]