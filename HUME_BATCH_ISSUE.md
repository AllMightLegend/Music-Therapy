# Hume Batch API Issue - Jobs Stuck in QUEUED Status

## Problem
The Hume batch jobs API is returning **"QUEUED"** status indefinitely. Jobs submitted to `https://api.hume.ai/v0/batch/jobs` never transition to `PROCESSING` or `COMPLETED`.

**Evidence:**
- Job submission succeeds (returns valid job ID).
- Polling `/predictions` endpoint returns HTTP 202 (job not ready) or 400 with message `"Job is still queued"`.
- Job details (GET `/v0/batch/jobs/{job_id}`) consistently show `"status":"QUEUED"`.
- Intermittent HTTP 500 errors from Cloudflare (Mumbai) on predictions endpoint.
- Multiple jobs affected; pattern is consistent.

## Possible Causes
1. **Hume backend outage or transient issue** — The batch processing worker is down or overloaded.
2. **Account/quota limits** — API key or account has hit rate limits or quota.
3. **Service degradation** — Hume infrastructure (Mumbai region) is experiencing issues.

## Immediate Actions

### 1. Check Hume Status
Visit **https://status.hume.ai** to check for ongoing incidents or scheduled maintenance.

### 2. Contact Hume Support
If the status page shows no issues, open a support ticket with:
- **Job IDs:**
  - `37877b8b-2ba0-434d-ba8e-2522dca50cbf` (stuck since ~15:51 UTC)
  - `a186a612-1ed1-4195-bc83-f05c3f6548e6` (stuck since ~15:53 UTC)
- **API Key** (last 4 digits for reference)
- **Region** (jobs submitted from India, using Mumbai Cloudflare endpoint)
- **Timestamp and Ray IDs** from Cloudflare 500 errors (e.g., `9a08a4546b90fb88`)

### 3. Retry Later
Hume batch queuing issues often resolve within minutes to hours. Try submitting a new job in 15–30 minutes.

## Workarounds

### Option A: Manual Mood Input (Immediate)
- Use the **"Start with Manual Input"** button in the app.
- Users select mood manually instead of relying on facial detection.
- Playlist recommendation logic is unaffected.

### Option B: WebSocket Streaming API (Recommended Long-term)
Switch from batch polling to real-time WebSocket streaming:
- **Advantage:** Real-time results (no queueing), persistent connection.
- **Disadvantage:** Requires async rewrite; integration effort.
- **Implementation:** Use `wss://api.hume.ai/v0/stream/models` with face model.

### Option C: Fallback to Local ML (Not Recommended)
Re-introduce DeepFace or TensorFlow for local inference:
- **Advantage:** Works offline, no API dependency.
- **Disadvantage:** Slow (~2–5s per frame), high CPU/memory, requires GPU for speed.

## Current Code State

### Batch API (Current)
- **File:** `emotion_detector.py`
- **Functions:** `_submit_job()`, `_poll_for_predictions()`, `_get_job_details()` (diagnostic)
- **Status:** Submission works; polling fails due to Hume backend issues.

### Removed
- SDK-based submission (AsyncHumeClient) — caused `asyncio.run()` conflicts with Streamlit's event loop.

## Notes for Future
- **Batch API is not ideal for real-time/interactive apps** (e.g., webcam-based mood detection). Batch is designed for bulk offline processing, not live interaction.
- **WebSocket streaming** is the correct choice for interactive emotion detection from webcam frames.
- Once Hume backend recovers, test with a clean API key or account to rule out quota issues.

---

**Last Updated:** 2025-11-18 21:25 UTC  
**Test Date:** Symptoms observed from ~15:41 UTC onwards.
