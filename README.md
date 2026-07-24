# Kobo Scan App
### Handwritten Form → KoboToolbox Automation

---

## What This Does
Data collectors take a photo of a completed paper form on their phone.
The app scans it, extracts all fields using AI, shows a review screen,
and submits directly to KoboToolbox. No manual data entry needed.

---

## Architecture
```
Phone Camera / Photo
       ↓
   Web App (this app — opens in any browser via link)
       ↓
   Image validation, orientation correction & quality scoring
       ↓
   Google Vision OCR (extracts all text from the image)
       ↓
   Claude AI (maps OCR text → Kobo field values)
       ↓
   Deterministic form-schema validation & calculated confidence
       ↓
   Data Collector Reviews only flagged fields & Confirms
       ↓
   KoboToolbox API (submission)
```

---



## Setup — Step by Step

### 1. Get Your Google Vision API Key
1. Go to https://console.cloud.google.com
2. Create a new project (or use existing)
3. Enable **Cloud Vision API**
4. Go to Credentials → Create Credentials → API Key
5. Copy the key

### 2. Get Your Kobo API Token
1. Log into https://kf.kobotoolbox.org
2. Go to Account Settings (top right)
3. Scroll to **API Token**
4. Copy the token

### 3. Deploy to Render.com
1. Push this project to a GitHub repository
2. Go to https://render.com → New → Web Service
3. Connect your GitHub repo
4. Set environment variables in Render dashboard:
   - `KOBO_TOKEN` = your Kobo token
   - `GOOGLE_VISION_API_KEY` = your Google Vision key
5. Deploy — Render will give you a URL like `https://kobo-scan-app.onrender.com`

### 4. Share the Link
Share `https://your-app-name.onrender.com` with data collectors.
That's it. No app installation. Works on any phone browser.

---

## Adding a New Project/Form
1. Update `config/field_map.json` with new `asset_uid` and fields
2. Or create separate config files per project and use `?form=project_code`
   (multi-form support can be added in a future version)

---

## Local Development
```bash
cd kobo-scan-app
cp .env.example .env
# Fill in .env values

pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
# Open http://localhost:8000
```

---

## Known Limitations
- Requires internet connection (no offline mode)
- OCR accuracy depends on handwriting clarity and photo quality
- The preview/review step is mandatory — collectors must confirm before submitting
- Free tier on Render may sleep after 15 minutes of inactivity (first request takes ~30s)
  - Upgrade to $7/month paid tier to avoid this in production

---

## Reliability and data-quality safeguards

- Images are restricted to JPEG, PNG, or WebP, size-limited, decoded before use,
  EXIF-oriented, gently enhanced, and assigned a separate 0–100 quality score.
- AI output is normalised and validated against the configured field type and valid
  Kobo choices. Invalid and missing values require human review; they cannot be sent
  to Kobo.
- Confidence is calculated from AI signal, image quality, and validation findings.
  The default auto-accept threshold is `90`; configure it globally or per field.
- The local audit store records source hashes, quality results, OCR text, AI results,
  validation, final data, and submission state. Image hashes produce a duplicate
  warning; a processing ID makes repeated submit requests idempotent.
- HTTP connections are reused and transient external failures are retried with backoff.

## Configuration additions

Copy `.env.example` to `.env`. In addition to the three provider keys, set
`CORS_ORIGINS` in production. `AUDIT_DB_PATH` defaults to local SQLite; Render's
ephemeral filesystem is not suitable for a durable audit trail, so production needs
a persistent disk or a migration of `backend/audit.py` to managed Postgres.

Existing form JSON files remain compatible. Optional field properties now supported:

```json
{"required": true, "min": 0, "max": 100, "confidence_threshold": 85}
```

## Verification

After installing development dependencies (`pip install -r backend/requirements-dev.txt`), run:

```bash
python -m pytest backend/test_validation.py -q
python -m compileall backend
```
