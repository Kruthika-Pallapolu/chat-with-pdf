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

`CWP_EMBEDDING_BATCH_SIZE` is optional and defaults to `8`. The only accepted values are `8` and `12`; malformed or unsupported values log a generic warning and fall back to `8`. It is read at process startup and changes embedding microbatching only; it does not change the model or vector settings.

## Embedding batch A/B benchmark

`CWP_EMBEDDING_BATCH_SIZE` accepts only `8` or `12`, is read at process startup, and defaults safely to `8` when unset or invalid. Keep the production service unset or set to `8`; use a separate Render staging service for comparison. The embedding log includes the selected batch size, elapsed time, and `process_peak_rss_mb`. That RSS is the process-lifetime high-water mark from Python's `resource` API, not a per-call peak; it can be unavailable on platforms without that API and can include memory used before the current upload.

For a reproducible Render comparison:

1. From the reviewed production base, create and push a benchmark branch containing only the intended files (do not add local backups):

   ```sh
   git switch -c benchmark/embedding-batch-8-vs-12
   git add .env.example DEPLOYMENT.md server.py src/embedder.py tests/test_citations.py tests/test_embedder.py
   git commit -m "Make embedding batch size configurable for benchmark"
   git push -u origin benchmark/embedding-batch-8-vs-12
   ```

2. In the Render Dashboard, create a separate web service from the same repository and select `benchmark/embedding-batch-8-vs-12` as its branch. Use the same instance size and runtime settings as production, a separate persistent disk, and a staging hostname in `ALLOWED_HOSTS`. Copy required environment values directly in Render, but do not point staging at production data or expose secrets in logs.
3. In the staging service environment, set `CWP_EMBEDDING_BATCH_SIZE=8`, save, and wait for the deploy to finish. Upload the same PDF twice: the first upload warms the model; record the second upload's `pdf_processing stage=embedding_generation` log line and memory metrics.
4. Change only `CWP_EMBEDDING_BATCH_SIZE` to `12`, save, and wait for the restart/deploy. Upload that same PDF twice again; record the second upload's log line and memory metrics. Keep the service awake between the two uploads in each pair and avoid other requests during the measurement window.
5. Compare `chunks`, `batch_size`, and `duration_ms` in the logs. Compare the process high-water value as a secondary signal. In the Render Dashboard, open the staging service's **Metrics** page and inspect the CPU and memory graphs over the upload windows; use the same graph range and view the memory value or percent consistently for both runs. Render's [service metrics](https://render.com/docs/service-metrics) show service memory over time, so correlate the graph with the logs and do not treat it as a precise per-request peak.
6. Leave production at batch size `8`. Do not promote batch size `12` unless the measured latency and memory headroom are acceptable.

The app's existing upload rate limit allows five uploads per hour by default, so the two warm-up/measurement pairs fit within one hour. For more repetitions, wait for the rate-limit window to roll over or change the limit only on the isolated benchmark service.

Start one process with `python server.py`. Production mode disables reload and configures one Uvicorn worker. Keep one worker: the session locks and in-memory document cache are process-local, and multi-worker behavior has not been verified. `requirements.txt` declares the Python dependencies; the deployment environment still needs network access to install them and, on a cold start without a cached model, download `all-MiniLM-L6-v2` from Hugging Face. No provider-specific build file or clean-environment install check is currently included.

## Data handling and service limits

Do not place `.env`, local PDFs, `data/`, virtual environments, caches, or user-uploaded documents in a deployment artifact. These are excluded by `.gitignore`, but verify the actual source bundle produced by your host. Configure a persistent volume for `CWP_DATA_DIR`; the process writes session PDFs, derived indexes, conversation data, a SQLite database, and a rate-limit key there.

Document questions and relevant retrieved PDF excerpts are sent to Gemini when `GEMINI_API_KEY` is configured. The embedding model runs locally after it is available. Review the model provider's data terms and disclose this processing to users before accepting private documents. The frontend currently loads PDF.js, Supabase JS, and fonts from third-party CDNs, so the UI depends on those services being reachable.

Anonymous sessions are rate-limited and quota-limited, but those limits do not provide account identity, abuse prevention guarantees, or a service-level commitment. Free hosting tiers may sleep, have slow cold starts, lack durable storage, restrict outbound model downloads, or provide insufficient memory/CPU for PDF parsing and embedding. Confirm the host's volume, resource, egress, and cost limits before deployment.

The variables in `.env.example` document defaults for local development and optional limits. Set production values in the hosting environment, especially the host allowlist, persistent data path, proxy trust list, quotas, and Gemini key. Never publish `.env.example` with populated secrets.
