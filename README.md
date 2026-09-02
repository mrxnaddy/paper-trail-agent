# 📋 Paper Trail — AI Bureaucracy Navigator (Pakistan)

Paper Trail is a conversational AI agent that helps Pakistani citizens navigate
common government processes — CNIC renewal, passport applications, driving
licenses, and vehicle registration — with clear, step-by-step guidance in
English, Urdu, or Roman Urdu.

It answers from a **verified local knowledge base** first, and only falls
back to **live web search** when a topic isn't covered locally — always
showing a **Confidence Score** so users know how much to trust the answer.

---

## ✨ Features

- Chat interface (ask in English / Urdu / Roman Urdu)
- Local knowledge base for CNIC, passport, driving license, vehicle registration
- Live web search fallback (Tavily) for anything not in the local KB
- Confidence Score (High / Medium / Low) with source links when applicable
- Document checklist tracker with progress bar
- Session memory — ask follow-ups like "what if I'm abroad?"
- Language toggle in the sidebar (English / Urdu)
- Graceful error handling — no crashes on missing/invalid API keys

---

## 🗂 Project Structure

```
paper-trail-agent/
├── app.py                     # Main Streamlit entry point
├── agent.py                   # Core agent logic (intent detection, response generation)
├── knowledge_base.py          # Functions to query/update local KB
├── search_tool.py             # Web search fallback integration
├── utils.py                   # Helper functions (language detection, formatting)
├── data/
│   └── knowledge_base.json    # Pre-populated common processes
├── requirements.txt
├── .env.example                # Template for API keys (no real keys committed)
├── .gitignore
├── README.md
└── .streamlit/
    └── config.toml
```

---

## 1. Local Setup (VS Code)

### Prerequisites
- Python 3.11+
- VS Code with the Python extension
- Git

### Steps

```bash
# 1. Clone or open the project folder in VS Code
cd paper-trail-agent

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the env template and add your real API keys
cp .env.example .env
# then edit .env in VS Code and paste your keys

# 5. Load the .env file's variables into your shell (or use a tool like python-dotenv
#    — for the simplest local run, just export them manually):
export ANTHROPIC_API_KEY=your_key_here     # macOS/Linux
export TAVILY_API_KEY=your_key_here
# On Windows (PowerShell): $env:ANTHROPIC_API_KEY="your_key_here"

# 6. Run the app
streamlit run app.py
```

The app will open automatically at `http://localhost:8501`.

> **Note:** The app works even without API keys configured — it will still
> answer from the local knowledge base, it just won't be able to handle
> free-form follow-up questions or live web search, and will tell the user
> so instead of crashing.

---

## 2. Getting API Keys

### Anthropic (Claude) API key
1. Go to [console.anthropic.com](https://console.anthropic.com/)
2. Sign up / log in
3. Navigate to **API Keys** and create a new key
4. Paste it into your `.env` file as `ANTHROPIC_API_KEY`

### Tavily (web search) API key
1. Go to [tavily.com](https://tavily.com/)
2. Sign up for a free account (generous free tier, no credit card required for basic use)
3. Copy your API key from the dashboard
4. Paste it into your `.env` file as `TAVILY_API_KEY`

Both are optional but recommended for the full experience — see the note above.

---

## 3. Push to GitHub

```bash
# From inside the paper-trail-agent/ folder
git init
git add .
git status   # double-check .env is NOT listed (it should be gitignored)
git commit -m "Initial commit: Paper Trail bureaucracy navigator agent"

# Create a new repo on GitHub first (via github.com → New repository),
# then link and push:
git remote add origin https://github.com/<your-username>/paper-trail-agent.git
git branch -M main
git push -u origin main
```

---

## 4. Deploy to Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io/) and sign in with GitHub
2. Click **"New app"**
3. Select your `paper-trail-agent` repository, branch `main`, and set the
   main file path to `app.py`
4. Click **"Advanced settings"** → **Secrets**, and add your keys in TOML format:
   ```toml
   ANTHROPIC_API_KEY = "your_anthropic_api_key_here"
   TAVILY_API_KEY = "your_tavily_api_key_here"
   ```
5. Click **"Deploy"**

That's it — no extra manual steps are needed beyond setting these two secrets.
Streamlit Cloud will install `requirements.txt` automatically and launch `app.py`.

---

## 5. Demo Script (matches the required test scenario)

1. Type: `mera CNIC kho gaya hai, Islamabad mein rehta hoon`
   → Agent returns the CNIC checklist, fees, nearest NADRA office info, and a
   High confidence score (matched from the local knowledge base).
2. Type: `agar main out of country hoon to?`
   → Agent adapts the previous CNIC answer to explain the overseas Pakistani
   process, referencing the earlier context (via session memory + LLM, with a
   static fallback if no LLM key is configured).

---

## ⚠️ Disclaimer

Government fees, required documents, and processing times change periodically.
Paper Trail's local knowledge base entries are marked with a "last verified"
date — always confirm critical details (especially fees) with the relevant
official office or website before your visit. Live web search results are
shown with source links and a Low/Medium confidence label so you can verify
them independently.

---

## 🛠 Manual Steps You Still Need To Do

- [ ] Sign up for an Anthropic API key and add billing if needed for production use
- [ ] Sign up for a Tavily API key (free tier)
- [ ] Create the GitHub repository and push this code
- [ ] Add both keys as Streamlit Cloud secrets when deploying
- [ ] Periodically review `data/knowledge_base.json` and update fees/timelines,
      since these change and the "last_verified" dates will go stale
