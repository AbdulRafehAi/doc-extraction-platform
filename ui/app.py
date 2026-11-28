# ui/app.py - Streamlit screen for uploading invoices and reviewing results

import json
import os

import httpx
import pandas as pd
import streamlit as st

# How this container reaches the API, and how YOUR browser reaches it
API_URL = os.getenv("API_URL", "http://localhost:8000")
PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "http://127.0.0.1:8000")

LINE_COLUMNS = ["description", "quantity", "unit_price", "amount"]

st.set_page_config(page_title="Invoice Extraction", layout="wide")
st.title("Document Extraction Platform")


def call_api(method: str, path: str, **kwargs):
    """Call our FastAPI backend and return the JSON answer."""
    response = httpx.request(method, f"{API_URL}{path}", timeout=60, **kwargs)
    response.raise_for_status()
    return response.json()


def as_float(value):
    """number_input needs a float or None (not an int)."""
    return None if value is None else float(value)


def upload_tab():
    uploaded = st.file_uploader("Choose an invoice (PDF)", type=["pdf"])
    if uploaded and st.button("Upload and extract"):
        document = call_api(
            "POST",
            "/documents/upload",
            files={"file": (uploaded.name, uploaded.getvalue(), "application/pdf")},
        )
        call_api("POST", f"/documents/{document['id']}/extract")
        st.success(
            f"Document {document['id']} uploaded. Extraction takes about a minute. "
            "Press Refresh to see the status."
        )

    st.subheader("All documents")
    st.button("Refresh")
    documents = call_api("GET", "/documents")
    if documents:
        table = pd.DataFrame(documents)
        st.dataframe(
            table[["id", "filename", "status", "error_message", "created_at"]],
            hide_index=True,
        )
    else:
        st.info("No documents yet.")


def review_tab():
    queue = call_api("GET", "/extractions/review")
    if not queue:
        st.success("Nothing to review. Every extraction passed the checks.")
        return

    labels = {
        item["id"]: f"Extraction {item['id']} (document {item['document_id']})"
        for item in queue
    }
    chosen = st.selectbox(
        "Choose an extraction to review", list(labels), format_func=labels.get
    )
    item = next(x for x in queue if x["id"] == chosen)
    key = item["id"]

    problems = "\n".join(f"- {text}" for text in item["validation_errors"] or [])
    st.warning("The checks found these problems:\n\n" + problems)
    st.markdown(
        f"[Open the original invoice in a new tab]"
        f"({PUBLIC_API_URL}/documents/{item['document_id']}/file)"
    )

    with st.form(f"review_form_{key}"):
        left, right = st.columns(2)
        vendor = left.text_input("Vendor name", item["vendor_name"] or "", key=f"vendor_{key}")
        number = left.text_input("Invoice number", item["invoice_number"] or "", key=f"number_{key}")
        date_text = left.text_input("Invoice date (YYYY-MM-DD)", item["invoice_date"] or "", key=f"date_{key}")
        currency = left.text_input("Currency (3 letters)", item["currency"] or "", key=f"currency_{key}")
        subtotal = right.number_input("Subtotal", value=as_float(item["subtotal"]), step=0.01, format="%.2f", key=f"subtotal_{key}")
        tax = right.number_input("Tax", value=as_float(item["tax"]), step=0.01, format="%.2f", key=f"tax_{key}")
        total = right.number_input("Total", value=as_float(item["total"]), step=0.01, format="%.2f", key=f"total_{key}")

        st.write("Line items (you can add or delete rows)")
        lines = pd.DataFrame(item["line_items"] or [], columns=LINE_COLUMNS)
        edited = st.data_editor(
            lines,
            num_rows="dynamic",
            key=f"lines_{key}",
            column_config={
                "quantity": st.column_config.NumberColumn(),
                "unit_price": st.column_config.NumberColumn(),
                "amount": st.column_config.NumberColumn(),
            },
        )

        save = st.form_submit_button("Save corrections")
        approve = st.form_submit_button("Save and approve")

    if save or approve:
        rows = json.loads(edited.to_json(orient="records"))
        rows = [r for r in rows if any(v not in (None, "") for v in r.values())]
        body = {
            "vendor_name": vendor or None,
            "invoice_number": number or None,
            "invoice_date": date_text or None,
            "currency": currency or None,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "line_items": rows,
        }
        try:
            call_api("PUT", f"/extractions/{key}", json=body)
            if approve:
                call_api("POST", f"/extractions/{key}/approve")
            st.toast("Saved")
            st.rerun()
        except httpx.HTTPStatusError as error:
            st.error(f"The API rejected this: {error.response.text}")


try:
    tab_upload, tab_review = st.tabs(["Upload", "Review"])
    with tab_upload:
        upload_tab()
    with tab_review:
        review_tab()
except httpx.ConnectError:
    st.error("Cannot reach the API. Is the api container running?")