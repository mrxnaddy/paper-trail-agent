"""
knowledge_base.py
------------------
Loads and queries the local JSON knowledge base (data/knowledge_base.json).

The KB is a dict of "process records" keyed by an internal id
(e.g. "cnic_renewal"). Each record has a "keywords" list used for
simple substring/overlap matching against user queries.

This is intentionally simple (no embeddings/vector DB) so the app
has zero extra infrastructure to deploy — appropriate for a hackathon
demo on Streamlit Community Cloud.
"""

import json
import os
from typing import Optional

KB_PATH = os.path.join(os.path.dirname(__file__), "data", "knowledge_base.json")

_kb_cache: Optional[dict] = None


def load_kb() -> dict:
    """Load the knowledge base from disk, caching it in memory."""
    global _kb_cache
    if _kb_cache is None:
        try:
            with open(KB_PATH, "r", encoding="utf-8") as f:
                _kb_cache = json.load(f)
        except FileNotFoundError:
            # Graceful fallback: empty KB rather than a crash.
            _kb_cache = {}
        except json.JSONDecodeError:
            _kb_cache = {}
    return _kb_cache


def find_matching_process(query: str) -> Optional[tuple[str, dict]]:
    """
    Try to match a free-text user query against a KB record's keywords.

    Returns (process_id, record) for the best match, or None if nothing
    scores above the minimum threshold.
    """
    if not query:
        return None

    kb = load_kb()
    query_lower = query.lower()

    best_id = None
    best_record = None
    best_score = 0

    for process_id, record in kb.items():
        score = 0
        for kw in record.get("keywords", []):
            if kw.lower() in query_lower:
                # Longer keyword matches are stronger signals than short ones
                score += len(kw.split())
        if score > best_score:
            best_score = score
            best_id = process_id
            best_record = record

    if best_score == 0:
        return None

    return best_id, best_record


def get_process_by_id(process_id: str) -> Optional[dict]:
    """Direct lookup by known process id."""
    return load_kb().get(process_id)


def list_all_processes() -> dict:
    """Return the whole KB — used for the sidebar 'browse topics' list."""
    return load_kb()
