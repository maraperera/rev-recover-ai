from typing import Any, Dict, List, Optional
import httpx
from config.settings import settings


class SAPClient:
    def __init__(self) -> None:
        self.base_url = settings.SAP_SANDBOX_BASE_URL.rstrip("/")
        self.headers = {
            "APIKey": settings.SAP_API_KEY,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def get_purchase_order(self, po_number: str) -> Optional[Dict[str, Any]]:
        """Fetch Purchase Order Header and associated line items by PO Number."""
        endpoint = (
            f"{self.base_url}/API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder('{po_number}')"
            f"?$expand=to_PurchaseOrderItem"
        )
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(endpoint, headers=self.headers)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            return data.get("d", {})

    async def list_sample_purchase_orders(self, top: int = 5) -> List[Dict[str, Any]]:
        """List live sandbox purchase orders for validation and testing."""
        endpoint = (
            f"{self.base_url}/API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder"
            f"?$top={top}&$expand=to_PurchaseOrderItem"
        )
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(endpoint, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            return data.get("d", {}).get("results", [])

    async def search_supplier_invoices(
        self, supplier_id: str, fiscal_year: str = "2024"
    ) -> List[Dict[str, Any]]:
        """Retrieve historical invoices from SAP to detect duplicates or over-billings."""
        endpoint = (
            f"{self.base_url}/API_SUPPLIERINVOICE_PROCESS_SRV/A_SupplierInvoice"
            f"?$filter=InvoicingParty eq '{supplier_id}' and FiscalYear eq '{fiscal_year}'"
            f"&$expand=to_SuplrInvcItemPurOrdRef"
        )
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(endpoint, headers=self.headers)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            data = response.json()
            return data.get("d", {}).get("results", [])