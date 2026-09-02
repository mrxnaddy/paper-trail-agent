"""
utils.py
--------
Small, dependency-light helper functions used across the app:
- language detection (English vs Roman Urdu / Urdu script)
- text formatting helpers for the chat UI
- simple keyword cleanup

Kept deliberately simple (no heavy NLP libraries) so the app installs
fast and works reliably on Streamlit Community Cloud's free tier.
"""

import re

# A small set of very common Roman Urdu words/particles.
# This is NOT a full language model — it's a lightweight heuristic
# good enough to decide "should I reply in Urdu-flavored text or plain English?"
ROMAN_URDU_MARKERS = {
    "mera", "meri", "mere", "hai", "hain", "kya", "kaise", "kahan", "kab",
    "kho", "gaya", "gayi", "gaye", "rehta", "rehti", "hoon", "hun", "ho",
    "abroad", "bahar", "mulk", "agar", "to", "toh", "chahiye", "karna",
    "karni", "karo", "kro", "banwana", "banwani", "kaha", "wala", "wali",
    "nahi", "nhi", "theek", "acha", "yaar", "bhai", "sahab", "sir",
    "madam", "please", "plz", "plzz", "mje", "mujhe", "mujy", "apna",
    "apni", "kesy", "kesay", "kese",
}


def detect_language(text: str) -> str:
    """
    Very lightweight language detector.

    Returns one of: "urdu_script", "roman_urdu", "english"

    - "urdu_script": text contains actual Urdu/Arabic unicode characters
    - "roman_urdu": text is in Latin script but uses common Roman Urdu words
    - "english": everything else (default/fallback)
    """
    if not text or not text.strip():
        return "english"

    # Check for Urdu/Arabic script unicode range
    if re.search(r"[\u0600-\u06FF]", text):
        return "urdu_script"

    # Check for Roman Urdu markers
    words = re.findall(r"[a-zA-Z]+", text.lower())
    if not words:
        return "english"

    marker_hits = sum(1 for w in words if w in ROMAN_URDU_MARKERS)
    # If a meaningful fraction of words are Roman Urdu markers, treat as Roman Urdu
    if marker_hits >= 1 and (marker_hits / max(len(words), 1)) >= 0.15:
        return "roman_urdu"

    return "english"


def clean_query(text: str) -> str:
    """Trim whitespace and collapse repeated spaces/punctuation for matching."""
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def confidence_badge(level: str) -> str:
    """Return a small colored emoji + label for the confidence score."""
    level = level.lower()
    mapping = {
        "high": "🟢 High",
        "medium": "🟡 Medium",
        "low": "🔴 Low",
    }
    return mapping.get(level, "🟡 Medium")


def format_roadmap(record: dict, lang_ui: str, confidence: str, source_note: str,
                    source_links: list | None = None) -> str:
    """
    Format a knowledge-base record (or a web-search-derived dict of the same
    shape) into the standard 6-part roadmap the spec requires:
      1. Summary
      2. Numbered checklist of documents
      3. Fees
      4. Processing time
      5. Office/department + how to locate
      6. Warnings / common mistakes

    lang_ui: "en" or "ur" — which language field to prefer for bilingual fields.
    """
    title = record["title"].get(lang_ui, record["title"].get("en", ""))
    summary = record["summary"].get(lang_ui, record["summary"].get("en", ""))
    office = record["office"].get(lang_ui, record["office"].get("en", ""))

    docs = record.get("documents", [])
    docs_md = "\n".join(f"{i+1}. {d}" for i, d in enumerate(docs)) or "_Not available._"

    fees = record.get("fees", {})
    if isinstance(fees, dict):
        fee_lines = []
        for k, v in fees.items():
            if k == "note":
                continue
            label = k.replace("_", " ").title()
            fee_lines.append(f"- **{label}:** {v}")
        fees_md = "\n".join(fee_lines) if fee_lines else "_Not available._"
        if "note" in fees:
            fees_md += f"\n\n_Note: {fees['note']}_"
    else:
        fees_md = str(fees)

    processing_time = record.get("processing_time", "Not available")
    how_to_locate = record.get("how_to_locate", "")

    warnings = record.get("warnings", [])
    warnings_md = "\n".join(f"- ⚠️ {w}" for w in warnings) if warnings else "_None listed._"

    badge = confidence_badge(confidence)

    links_md = ""
    if source_links:
        links_md = "\n\n**Sources:**\n" + "\n".join(f"- {u}" for u in source_links)

    out = f"""### {title}

**Confidence Score:** {badge}  _( {source_note} )_

**1. Summary**
{summary}

**2. Documents Checklist**
{docs_md}

**3. Fees**
{fees_md}

**4. Estimated Processing Time**
{processing_time}

**5. Office / Where to Go**
**{office}**
{how_to_locate}

**6. Warnings & Common Mistakes**
{warnings_md}
{links_md}
"""
    return out
