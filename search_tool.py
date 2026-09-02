"""
search_tool.py
---------------
Live web search fallback, used when a user's query doesn't match anything
in the local knowledge base (data/knowledge_base.json).

Uses the Tavily API (https://tavily.com) because it has a generous free
tier and returns clean, LLM-friendly summaries + source URLs — ideal for
a hackathon project. SerpAPI could be swapped in with a similar wrapper
if preferred; just replace the body of `web_search()`.

All functions fail *gracefully*: if the API key is missing or the
request fails for any reason, they return a dict with "error" set
instead of raising, so the calling agent code can show a friendly
message instead of crashing the app.
"""

import os
from typing import Optional

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False


def _get_api_key() -> Optional[str]:
    """Read the Tavily API key from environment / Streamlit secrets."""
    key = os.environ.get("TAVILY_API_KEY")
    if key:
        return key
    # Fallback: try Streamlit secrets if running inside Streamlit Cloud
    try:
        import streamlit as st
        return st.secrets.get("TAVILY_API_KEY")
    except Exception:
        return None


def web_search(query: str, max_results: int = 4) -> dict:
    """
    Perform a live web search for the given query.

    Returns a dict shaped like:
        {
            "ok": True,
            "answer": "short synthesized answer or None",
            "results": [{"title": ..., "url": ..., "content": ...}, ...]
        }
    or, on any failure:
        {
            "ok": False,
            "error": "human-readable error message"
        }
    """
    if not TAVILY_AVAILABLE:
        return {
            "ok": False,
            "error": (
                "Live web search is unavailable because the 'tavily-python' "
                "package is not installed. Add it to requirements.txt and "
                "redeploy, or answer using local knowledge base topics only."
            ),
        }

    api_key = _get_api_key()
    if not api_key:
        return {
            "ok": False,
            "error": (
                "Live web search is unavailable because TAVILY_API_KEY is not "
                "configured. Set it as an environment variable locally, or "
                "as a Streamlit Cloud secret. Falling back to local knowledge "
                "base information only."
            ),
        }

    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=f"{query} Pakistan official government process requirements fees",
            search_depth="basic",
            max_results=max_results,
            include_answer=True,
        )
        results = [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
            }
            for r in response.get("results", [])
        ]
        return {
            "ok": True,
            "answer": response.get("answer"),
            "results": results,
        }
    except Exception as e:  # noqa: BLE001 - deliberately broad for graceful fallback
        return {
            "ok": False,
            "error": f"Live web search failed ({type(e).__name__}). "
                     f"Showing best-effort answer based on general knowledge instead.",
        }
