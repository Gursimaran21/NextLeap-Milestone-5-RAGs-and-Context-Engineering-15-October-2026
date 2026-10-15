# Deploying to Streamlit Community Cloud

Get a permanent public URL like **`https://<your-app-name>.streamlit.app`** (no more
`localhost`). You need a **GitHub** account and a **Streamlit** account
(sign in at <https://share.streamlit.io> with GitHub — free).

---

## 1 · Push this project to GitHub

From the project root (`groww-milestone5/`):

```bash
git init
git add .
git commit -m "Groww Milestone 5 — Streamlit prototype"
git branch -M main
# create an EMPTY repo on github.com (any name, e.g. <your-repo>), then:
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

`.gitignore` already excludes `.env`, `.streamlit/secrets.toml`, `__pycache__/`,
`data/raw/*.csv` (may contain PII) and the generated logs — so **no secrets or PII** are pushed.

## 2 · Create the app

1. Go to <https://share.streamlit.io> → **Create app** → **Deploy a public app from GitHub**.
2. Repository: `<your-username>/<your-repo>`, Branch: `main`, **Main file path: `app.py`**.
3. Open **Advanced settings**:
   - **Python version:** 3.11 (or 3.12).
   - **Requirements file:** `requirements-cloud.txt` (this installs `google-genai` so live text works).
   - **Secrets:** paste the TOML below.
4. Click **Deploy**. First build takes 2–4 minutes; you'll get a URL like
   `https://<your-app-name>.streamlit.app`.

### Secrets (Advanced settings → Secrets)

```toml
GEMINI_API_KEY = "your-real-key-here"
# optional:
# GEMINI_MODEL = "gemini-2.5-flash"
```

The app mirrors `st.secrets` into the environment at startup, so `src/llm.py` finds the key
automatically. **No key?** The app still runs — it falls back to the deterministic offline
writer and every constraint is still enforced.

## 3 · Reboot / share

- **Reboot app** from the ⋮ menu after editing the requirements file.
- Share the `*.streamlit.app` URL. Anyone can open it; the prototype is public.

## Cloud caveats (important for a file-writing prototype)

Streamlit Community Cloud runs on an **ephemeral container with no persistent disk**:

- `outputs/` and `mcp/approval_log.jsonl` **reset whenever the app reboots or sleeps**.
  The demo still works (Run analysis → Approve & Execute → download files), but entries
  don't survive a restart.
- All visitors share one instance: one person's **Run analysis** changes what others see.
  That's fine for a demo — not for production.
- The **♻️ Reset demo artifacts** button clears the shared logs for everyone.

For a strictly private link, keep it local (LAN: `streamlit run app.py --server.address 0.0.0.0`)
or use a temporary tunnel instead.
