"""
app.py
------
Paper Trail — AI Bureaucracy Navigator (Pakistan)

Main Streamlit entry point. Run with:
    streamlit run app.py

See README.md for setup, API keys, and deployment instructions.
"""

import streamlit as st

import knowledge_base as kb
from agent import handle_message
from utils import detect_language

st.set_page_config(
    page_title="Paper Trail — Bureaucracy Navigator",
    page_icon="📋",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {"role": "user"/"assistant", "content": str}

if "lang_ui" not in st.session_state:
    st.session_state.lang_ui = "en"  # "en" or "ur"

if "checklist" not in st.session_state:
    st.session_state.checklist = {}  # {process_id: {doc_text: bool}}

if "active_process_id" not in st.session_state:
    st.session_state.active_process_id = None

if "query_counts" not in st.session_state:
    st.session_state.query_counts = {}  # simple analytics: process_id -> count


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("📋 Paper Trail")
    st.caption("AI Bureaucracy Navigator — Pakistan")

    lang_choice = st.radio(
        "Language / زبان",
        options=["English", "اردو"],
        index=0 if st.session_state.lang_ui == "en" else 1,
        horizontal=True,
    )
    st.session_state.lang_ui = "en" if lang_choice == "English" else "ur"

    st.divider()
    st.subheader("Browse Topics")
    all_processes = kb.list_all_processes()
    for pid, record in all_processes.items():
        label = record["title"].get(st.session_state.lang_ui, record["title"].get("en"))
        if st.button(label, key=f"topic_{pid}", use_container_width=True):
            st.session_state.active_process_id = pid
            st.session_state.messages.append({"role": "user", "content": label})
            st.rerun()

    st.divider()

    # --- Document Checklist Tracker ---
    st.subheader("✅ Document Checklist")
    if st.session_state.active_process_id:
        record = kb.get_process_by_id(st.session_state.active_process_id)
        if record:
            pid = st.session_state.active_process_id
            if pid not in st.session_state.checklist:
                st.session_state.checklist[pid] = {doc: False for doc in record.get("documents", [])}

            docs_state = st.session_state.checklist[pid]
            for doc in list(docs_state.keys()):
                docs_state[doc] = st.checkbox(doc, value=docs_state[doc], key=f"chk_{pid}_{hash(doc)}")

            total = len(docs_state) or 1
            done = sum(1 for v in docs_state.values() if v)
            st.progress(done / total, text=f"{done}/{total} documents ready")
    else:
        st.caption("Ask about a process (or pick a topic above) to see its document checklist here.")

    st.divider()
    if st.session_state.query_counts:
        st.subheader("📊 Most Asked (this session)")
        sorted_counts = sorted(st.session_state.query_counts.items(), key=lambda x: -x[1])
        for pid, count in sorted_counts[:5]:
            label = kb.get_process_by_id(pid)
            name = label["title"]["en"] if label else pid
            st.caption(f"{name}: {count}")

    st.divider()
    if st.button("🔄 Reset Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.active_process_id = None
        st.rerun()


# ---------------------------------------------------------------------------
# Main chat area
# ---------------------------------------------------------------------------
st.header("📋 Paper Trail — Bureaucracy Navigator")
st.caption(
    "Ask me about CNIC renewal, passport applications, driving licenses, "
    "vehicle registration, and more — in English, Urdu, or Roman Urdu."
)

# Render existing conversation
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
user_input = st.chat_input("e.g. mera CNIC kho gaya hai, Islamabad mein rehta hoon")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Looking this up..."):
            try:
                result = handle_message(
                    user_input,
                    st.session_state.messages[:-1],  # history before this turn
                    lang_ui=st.session_state.lang_ui,
                    active_process_id=st.session_state.active_process_id,
                )
            except Exception as e:
                # Top-level safety net: the app must never hard-crash on the user.
                result = {
                    "text": (
                        "Sorry, something went wrong while processing that request "
                        f"({type(e).__name__}). Please try rephrasing your question, "
                        "or ask about CNIC, passport, driving license, or vehicle registration."
                    ),
                    "matched_process_id": None,
                    "confidence": "low",
                    "used_search": False,
                }

        st.markdown(result["text"])

        if result.get("matched_process_id"):
            st.session_state.active_process_id = result["matched_process_id"]
            pid = result["matched_process_id"]
            st.session_state.query_counts[pid] = st.session_state.query_counts.get(pid, 0) + 1

    st.session_state.messages.append({"role": "assistant", "content": result["text"]})
    st.rerun()
