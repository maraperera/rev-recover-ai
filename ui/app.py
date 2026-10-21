import os
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1/audits")

st.set_page_config(page_title="RevRecover AI Portal", layout="wide", page_icon="⚖️")

st.title("⚖️ RevRecover AI — Enterprise Revenue Recovery Platform")
st.markdown(
    "Automated 3-way reconciliation engine comparing **Invoices vs. SAP S/4HANA POs vs. Contract SLAs**."
)

tab1, tab2 = st.tabs(["⚡ Run Invoice Audit", "📋 Review & Authorize Recoveries"])

with tab1:
    st.subheader("Ingest Supplier Invoice")
    sample_text = """INVOICE #INV-99021
Supplier: Global Industrial Solutions (ID: 1000042)
Purchase Order Ref: 4500000001
Date: 2024-10-15
Line Items:
Item 00010: Heavy Duty Industrial Ball Bearings
Quantity: 50 EA
Unit Price: $185.00
Line Total: $9,250.00
Payment Terms: Net 30
Total Gross: $9,250.00"""

    invoice_input = st.text_area("Raw Invoice Content (OCR/PDF text)", value=sample_text, height=220)

    if st.button("Start Agentic Audit", type="primary"):
        with st.spinner("Agents active: Extracting fields -> Checking SAP Sandbox -> Running RAG..."):
            try:
                res = requests.post(
                    f"{API_BASE_URL}/trigger", json={"raw_document_text": invoice_input}
                )
                res.raise_for_status()
                data = res.json()
                st.session_state["active_thread_id"] = data["thread_id"]
                st.session_state["report"] = data.get("audit_report")
                st.success(f"Audit Complete! Thread ID: {data['thread_id']}")
            except Exception as e:
                st.error(f"Execution failed: {str(e)}")

with tab2:
    st.subheader("Auditor Approval Queue (Human-in-the-Loop)")
    thread_id = st.text_input("Active Thread ID", value=st.session_state.get("active_thread_id", ""))

    if st.session_state.get("report"):
        report = st.session_state["report"]
        st.metric(
            label="Total Recoverable Overcharge",
            value=f"${report['total_recoverable']:.2f}",
            delta=f"{len(report['discrepancies'])} variances flagged",
            delta_color="inverse",
        )

        st.markdown("### Discrepancy Breakdown")
        for d in report["discrepancies"]:
            st.warning(
                f"**Item {d['item_id']} — {d['discrepancy_type']}**\n\n"
                f"- **Billed:** ${d['billed_amount']} | **Contract Cap:** ${d['entitled_amount']}\n"
                f"- **Overcharge:** ${d['recoverable_amount']}\n"
                f"- **Rule/Clause:** {d['clause_reference']}\n"
                f"- **Details:** {d['explanation']}"
            )

        st.markdown("### Generated Vendor Dispute Notice")
        st.text_area("Claude 3.5 Generated Memo", value=report["dispute_memo"], height=160)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Authorize Debit Memo & SAP Deduction", type="primary"):
                res = requests.post(
                    f"{API_BASE_URL}/review",
                    json={"thread_id": thread_id, "verdict": "APPROVED"},
                )
                if res.status_code == 200:
                    st.success("Recovery action authorized! Sent to SAP S/4HANA.")
        with col2:
            if st.button("❌ Dismiss Variance"):
                res = requests.post(
                    f"{API_BASE_URL}/review",
                    json={"thread_id": thread_id, "verdict": "REJECTED"},
                )
                if res.status_code == 200:
                    st.info("Discrepancy marked as dismissed.")