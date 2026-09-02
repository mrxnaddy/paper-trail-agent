"""
agent.py
--------
Core "Paper Trail" agent logic:
  1. Detect language of the user's message
  2. Try to match the query against the local knowledge base first
  3. If no local match, fall back to live web search (search_tool.py)
  4. Use an LLM (Gemini, via GEMINI_API_KEY) to:
        - handle contextual follow-up questions (e.g. "what if I'm abroad?")
        - turn raw web-search results into a structured roadmap when the
          local KB has nothing
  5. Return a dict the Streamlit UI can render directly

If no LLM API key is configured, the agent still works using the local
KB and simple template formatting — it just won't be able to handle
free-form follow-up questions as gracefully (it says so explicitly
rather than crashing).
"""

import os
from typing import Optional

import knowledge_base as kb
import search_tool
from utils import detect_language, format_roadmap, clean_query

try:
    from google import genai
    from google.genai import types as genai_types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


SYSTEM_PROMPT = """You are "Paper Trail", a helpful assistant that explains Pakistani
government / bureaucratic processes (CNIC, passport, driving license, vehicle
registration, property registration, etc.) in simple, accurate, step-by-step terms.

Rules:
- Always structure your answer as: 1) Summary 2) Numbered document checklist
  3) Fees 4) Estimated processing time 5) Office/department + how to locate it
  6) Warnings/common mistakes.
- If you are not fully certain about a specific fee or timeline, say so plainly
  rather than inventing a precise number.
- Reply in the same language style the user used (English, Urdu script, or Roman Urdu).
- Be concise, warm, and practical — the user is likely frustrated or in a hurry.
- If the user asks a follow-up question (e.g. "what if I'm abroad?"), adapt your
  PREVIOUS answer to the new condition rather than starting over from scratch.
"""


def _get_genai_client():
    """Read the Gemini API key from environment / Streamlit secrets and build a client."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GEMINI_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
        except Exception:
            api_key = None
    if not api_key or not GENAI_AVAILABLE:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None


def _llm_answer(user_message: str, conversation_history: list, context_note: str = "") -> Optional[str]:
    """
    Ask Gemini to produce a structured answer, optionally given extra
    context (e.g. relevant KB record text or web search snippets).
    Returns None if no LLM is configured or the call fails, so callers
    can fall back to template-based formatting.
    """
    client = _get_genai_client()
    if client is None:
        return None

    # Gemini uses role "model" instead of "assistant" for prior AI turns.
    contents = []
    for turn in conversation_history[-6:]:  # keep last few turns for context
        role = "model" if turn["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": turn["content"]}]})

    final_user_content = user_message
    if context_note:
        final_user_content = f"{user_message}\n\n[Reference information to ground your answer:]\n{context_note}"

    contents.append({"role": "user", "parts": [{"text": final_user_content}]})

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=genai_types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=1200,
            ),
        )
        return (response.text or "").strip() or None
    except Exception:
        return None



def handle_message(user_message: str, conversation_history: list, lang_ui: str = "en",
                    active_process_id: Optional[str] = None) -> dict:
    """
    Main entry point called by app.py for each new user message.

    active_process_id: the process the user was most recently discussing
        (tracked by the caller/UI across turns). Used so that vague
        follow-ups like "what if I'm abroad?" — which don't repeat any
        of the original keywords — can still be answered in context,
        even without an LLM configured.

    Returns:
        {
            "text": <markdown string to display>,
            "matched_process_id": <str or None>,
            "confidence": "high" | "medium" | "low",
            "used_search": bool,
        }
    """
    query = clean_query(user_message)
    detected_lang = detect_language(query)

    is_followup = len(conversation_history) > 0

    # --- Step 1: try local knowledge base first ---
    match = kb.find_matching_process(query)

    # If this looks like a vague follow-up (no fresh keyword match) but we
    # know which process the user was already discussing, treat that as
    # the match so context-dependent questions ("what if I'm abroad?")
    # still resolve correctly.
    if not match and is_followup and active_process_id:
        record = kb.get_process_by_id(active_process_id)
        if record:
            match = (active_process_id, record)

    if match and not is_followup:
        process_id, record = match
        roadmap_md = format_roadmap(
            record,
            lang_ui=lang_ui,
            confidence="high",
            source_note="Sourced from verified local knowledge base",
        )
        # If an LLM is available, let it lightly personalize tone/language,
        # but the structured facts always come from the trusted KB text above.
        return {
            "text": roadmap_md,
            "matched_process_id": process_id,
            "confidence": "high",
            "used_search": False,
        }

    if match and is_followup:
        # Follow-up question about an already-identified process (e.g. "what if I'm abroad?")
        process_id, record = match
        overseas_note = record.get("overseas_note", {})
        
        # Check if the query is specifically asking about fees or general local details instead of overseas
        query_lower = query.lower()
        is_fee_query = "fee" in query_lower or "kitne" in query_lower or "price" in query_lower or "cost" in query_lower or "paisa" in query_lower or "amount" in query_lower
        is_overseas_query = "abroad" in query_lower or "foreign" in query_lower or "bahar" in query_lower or "overseas" in query_lower or "visa" in query_lower

        # Call LLM first with contextual prompt
        llm_reply = _llm_answer(
            query,
            conversation_history,
            context_note=(
                f"Process: {record['title'].get('en')}\n"
                f"Full record data: {record}"
            ),
        )
        if llm_reply:
            return {
                "text": llm_reply,
                "matched_process_id": process_id,
                "confidence": "medium",
                "used_search": False,
            }

        # If LLM failed and user is asking about fees or general info (not overseas), return the clean roadmap
        if is_fee_query or not is_overseas_query:
            roadmap_md = format_roadmap(
                record,
                lang_ui=lang_ui,
                confidence="medium",
                source_note="Sourced from verified local knowledge base",
            )
            return {
                "text": roadmap_md,
                "matched_process_id": process_id,
                "confidence": "medium",
                "used_search": False,
            }

        # No LLM configured — fall back to the static overseas_note field if specifically an overseas query
        if overseas_note:
            note_text = overseas_note.get(lang_ui, overseas_note.get("en", ""))
            return {
                "text": f"**Regarding your follow-up:**\n\n{note_text}",
                "matched_process_id": process_id,
                "confidence": "medium",
                "used_search": False,
            }

    # --- Step 2: try LLM directly for follow-ups even without a KB re-match ---
    if is_followup:
        llm_reply = _llm_answer(query, conversation_history)
        if llm_reply:
            return {
                "text": llm_reply,
                "matched_process_id": None,
                "confidence": "medium",
                "used_search": False,
            }

    # --- Step 3: no local match — fall back to live web search ---
    search_result = search_tool.web_search(query)

    if not search_result.get("ok"):
        # Graceful degradation: never crash, always explain what happened.
        fallback_msg = (
            f"I couldn't find this in my verified local knowledge base, and live web "
            f"search isn't available right now ({search_result.get('error')}).\n\n"
            f"Try rephrasing your question, or ask about one of these supported topics: "
            f"CNIC renewal, passport renewal, driving license, or vehicle registration."
        )
        return {
            "text": fallback_msg,
            "matched_process_id": None,
            "confidence": "low",
            "used_search": False,
        }

    # Try to have the LLM turn search results into the structured roadmap format
    context_snippets = "\n\n".join(
        f"Source: {r['url']}\nTitle: {r['title']}\nContent: {r['content'][:600]}"
        for r in search_result["results"]
    )
    llm_reply = _llm_answer(query, conversation_history, context_note=context_snippets)

    links = [r["url"] for r in search_result["results"] if r.get("url")]

    if llm_reply:
        links_md = "\n\n**Sources:**\n" + "\n".join(f"- {u}" for u in links) if links else ""
        return {
            "text": llm_reply + links_md,
            "matched_process_id": None,
            "confidence": "medium",
            "used_search": True,
        }

    # No LLM available at all — show raw search answer/snippets as best effort
    raw_answer = search_result.get("answer") or "Here's what I found from a live web search:"
    snippets_md = "\n\n".join(f"**{r['title']}**\n{r['content'][:400]}...\n{r['url']}" for r in search_result["results"])
    links_md = "\n\n**Sources:**\n" + "\n".join(f"- {u}" for u in links) if links else ""
    return {
        "text": f"{raw_answer}\n\n{snippets_md}{links_md}\n\n_Note: this is unverified live search "
                f"information, not from the local knowledge base — confidence is Low. Please verify "
                f"with the relevant office before proceeding._",
        "matched_process_id": None,
        "confidence": "low",
        "used_search": True,
    }