# CWP deployment notes

## Current deployment scope

CWP currently supports an **anonymous-session demo**, not a public authenticated service. The browser may display an optional Supabase sign-in flow, but the FastAPI routes authorize requests with a server-issued anonymous session cookie; they do not validate a Supabase user identity. Do not rely on client-side gating to protect a public deployment. Add and verify server-side identity checks before opening the service to the public or storing sensitive documents.

Each session's PDF, index, answer memory, conversation history, rate limits, and session records live under `CWP_DATA_DIR`. Attach a persistent writable volume at that path. Read-only shared conversation snapshots use the same SQLite database, remain available across application restarts, and are lost if that volume is lost or rolled back. Shared links are immutable and currently have no revocation or automatic expiry. Keep the volume private and back it up according to the data-retention policy you choose. Expired sessions are cleaned up on requests; this is not a substitute for monitoring and volume capacity management.

## Build and start

Use Python 3.11 or newer with the packages in `requirements.txt`. A clean environment can be prepared with:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Set these deployment variables in the hosting platform's environment settings (do not commit their values):

- `CWP_ENV=production`
- `ALLOWED_HOSTS` to the exact public hostname, without a scheme or path
- `HOST=0.0.0.0`
- `PORT` to the port supplied by the hosting platform
- `CWP_DATA_DIR` to the persistent-volume mount path
- `FORWARDED_ALLOW_IPS` to the proxy IPs or ranges that the host documents; do not trust arbitrary forwarded headers
- `GEMINI_API_KEY` if Gemini-powered answers are required

For a 512 MB instance, also keep `CWP_NATIVE_THREAD_LIMIT=1`, `MAX_CONCURRENT_MODEL_REQUESTS=1`, `MAX_CONCURRENT_PDF_PROCESSES=1`, and `MAX_CONCURRENT_DOCUMENT_LOADS=1`. These values bound native thread pools and memory-heavy work across sessions; increasing them can increase peak memory.

Start one process with `python server.py`. Production mode disables reload and configures one Uvicorn worker. Keep one worker: the session locks and in-memory document cache are process-local, and multi-worker behavior has not been verified. `requirements.txt` declares the Python dependencies; the deployment environment still needs network access to install them and, on a cold start without a cached model, download `all-MiniLM-L6-v2` from Hugging Face. No provider-specific build file or clean-environment install check is currently included.

## Data handling and service limits

Do not place `.env`, local PDFs, `data/`, virtual environments, caches, or user-uploaded documents in a deployment artifact. These are excluded by `.gitignore`, but verify the actual source bundle produced by your host. Configure a persistent volume for `CWP_DATA_DIR`; the process writes session PDFs, derived indexes, conversation data, a SQLite database, and a rate-limit key there.

Document questions and relevant retrieved PDF excerpts are sent to Gemini when `GEMINI_API_KEY` is configured. The embedding model runs locally after it is available. Review the model provider's data terms and disclose this processing to users before accepting private documents. The frontend currently loads PDF.js, Supabase JS, and fonts from third-party CDNs, so the UI depends on those services being reachable.

Anonymous sessions are rate-limited and quota-limited, but those limits do not provide account identity, abuse prevention guarantees, or a service-level commitment. Free hosting tiers may sleep, have slow cold starts, lack durable storage, restrict outbound model downloads, or provide insufficient memory/CPU for PDF parsing and embedding. Confirm the host's volume, resource, egress, and cost limits before deployment.

The variables in `.env.example` document defaults for local development and optional limits. Set production values in the hosting environment, especially the host allowlist, persistent data path, proxy trust list, quotas, and Gemini key. Never publish `.env.example` with populated secrets.
