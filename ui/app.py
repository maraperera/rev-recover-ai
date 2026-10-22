import os
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1/audits")

st.set_page_config(page_title="RevRecover AI — Interactive Audit Portal", layout="wide", page_icon="⚖️")

st.title("⚖️ RevRecover AI — Enterprise Revenue Recovery Platform")
st.caption("Automated 3-way reconciliation engine comparing **Invoices vs. SAP S/4HANA POs vs. Contract SLAs**")

if "active_thread_id" not in st.session_state:
    st.session_state["active_thread_id"] = None
if "report" not in st.session_state:
    st.session_state["report"] = None
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

tab_audit, tab_review, tab_rag = st.tabs(["⚡ Ingest & Run", "📋 Audit Findings & HITL", "💬 Interactive Contract RAG"])

# --- TAB 1: Ingest & Run ---
with tab_audit:
    st.subheader("Invoice Ingestion & Extraction")
    sample_text = """INVOICE #INV-99021
Supplier: Global Industrial Solutions (ID: 1000042)
Purchase Order Ref: 4500000001
Date: 2024-10-15
Line Items:
Item 00010: Heavy Duty Industrial Ball Bearings
Quantity: 50 EA
Unit Price: \$185.00
Line Total: \$9,250.00
Payment Terms: Net 30
Total Gross: \$9,250.00"""

    invoice_input = st.text_area("Vendor Invoice Text / OCR Stream", value=sample_text, height=200)

    if st.button("🚀 Run Agentic Reconciliation", type="primary"):
        with st.spinner("Extracting invoice -> Querying SAP OData -> Running Contract RAG..."):
            try:
                res = requests.post(f"{API_BASE_URL}/trigger", json={"raw_document_text": invoice_input})
                res.raise_for_status()
                data = res.json()
                st.session_state["active_thread_id"] = data["thread_id"]
                st.session_state["report"] = data.get("audit_report")
                st.success(f"Audit completed! Session checkpoint: `{data['thread_id']}`")
                st.info("👉 Switch to the **'Audit Findings & HITL'** tab to review discrepancies or **'Interactive Contract RAG'** to query policies.")
            except Exception as e:
                st.error(f"Audit failed to trigger: {e}")

# --- TAB 2: Review & Human-in-the-Loop ---
with tab_review:
    st.subheader("Discrepancy Review & Human Authorization")
    thread_id = st.text_input("Active Audit Thread ID", value=st.session_state.get("active_thread_id") or "")

    if st.session_state.get("report"):
        report = st.session_state["report"]
        total_rec = report.get("total_recoverable", 0.0)
        discrepancies = report.get("discrepancies", [])

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Recoverable Overcharge", f"\${total_rec:,.2f}", delta="Variance Found", delta_color="inverse")
        col_m2.metric("Discrepant Items", len(discrepancies))
        col_m3.metric("Supplier ID", report.get("supplier_id", "N/A"))

        st.markdown("#### Flagged Variances")
        for d in discrepancies:
            with st.expander(f"⚠️ Item {d['item_id']} — {d['discrepancy_type']} (\${d['recoverable_amount']:,.2f})", expanded=True):
                col_a, col_b = st.columns(2)
                col_a.write(f"**Billed Amount:** \${d['billed_amount']:,.2f}")
                col_a.write(f"**Authorized Contract Cap:** \${d['entitled_amount']:,.2f}")
                col_b.write(f"**Contract Reference:** `{d['clause_reference']}`")
                col_b.write(f"**Audit Findings:** {d['explanation']}")

        st.markdown("#### Automated Vendor Dispute Letter")
        st.text_area("Generated Memo", value=report.get("dispute_memo", ""), height=150)

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("✅ Authorize SAP Debit Memo Deduction", type="primary"):
                res = requests.post(f"{API_BASE_URL}/review", json={"thread_id": thread_id, "verdict": "APPROVED"})
                if res.status_code == 200:
                    st.success("Debit memo approved and executed against SAP S/4HANA PO record!")
        with col_btn2:
            if st.button("❌ Dismiss Variance"):
                res = requests.post(f"{API_BASE_URL}/review", json={"thread_id": thread_id, "verdict": "REJECTED"})
                if res.status_code == 200:
                    st.warning("Audit variance dismissed by analyst.")
    else:
        st.info("No active audit report loaded. Run an audit in the first tab to inspect results.")

# --- TAB 3: Interactive Contract RAG ---
with tab_rag:
    st.subheader("💬 Interactive Contract & Policy Explorer")
    st.caption("Ask questions directly against vendor contracts, SAP pricing schedules, and reconciliation results.")

    current_thread = st.session_state.get("active_thread_id")
    if not current_thread:
        st.warning("Please run an invoice audit first to initialize the context session.")
    else:
        # Display previous chat messages
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Interactive query prompt
        if prompt := st.chat_input("Ask a question about pricing rules, SLA clauses, or calculation logic..."):
            st.session_state["chat_history"].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Searching contract vector embeddings & PO lineage..."):
                    try:
                        res = requests.post(
                            f"{API_BASE_URL}/chat",
                            json={"thread_id": current_thread, "query": prompt},
                        )
                        res.raise_for_status()
                        bot_response = res.json().get("answer", "No response generated.")
                    except Exception as err:
                        bot_response = f"Failed to retrieve answer: {err}"
                    st.markdown(bot_response)

            st.session_state["chat_history"].append({"role": "assistant", "content": bot_response})