# FreshTrack — Smart Food Expiry Tracker (Starter)

A Flask starter project for recording food items, viewing expiry status, uploading product photos, attempting OCR on package labels, reading barcodes, viewing simple ingredient-based recipe ideas, and recording user feedback.

## Run locally (Windows / VS Code)

1. Install Python 3.10 or newer.
2. Open this folder in VS Code.
3. Open Terminal → New Terminal.
4. Create a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

5. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

6. Run the app:

   ```powershell
   python app.py
   ```

7. Open http://127.0.0.1:5000

## Features in this starter

- Add food items with name, category, purchase date, expiry date, quantity, storage type, notes, and optional image.
- JSON-based inventory storage (suitable for a local demo, not multi-user production).
- Expiry status calculation and in-app alerts when the dashboard loads.
- 24-hour post-expiry cleanup that archives removed records in `data/history.json`.
- Browser-based barcode reading (ZXing CDN) and OCR text extraction from an uploaded photo (Tesseract.js CDN); both require internet access, camera permission where relevant, and user verification.
- Simple rule-based recipe ideas for a few common ingredients.
- Feedback logging to `data/feedback.json`.

## Important limitations

- OCR output can be wrong. Always verify names and dates from the package.
- Barcode scanning reads the code only; this starter does not query a product database.
- Expiry dates must be entered by the user unless manually corrected after OCR. It does not contain a trained CNN or ML expiry prediction model.
- Alerts are calculated when the dashboard is loaded. This starter does **not** implement scheduled background alerts or Web Push notifications.
- Feedback is recorded but does not train or improve an ML model.
- No user authentication is included; do not expose this starter publicly with private data.
- The expiry-date cleanup is a demo rule. Food safety cannot be determined by dates alone; follow package directions and food-safety guidance.

## Deploying to Render

For a simple Render Web Service:
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`

Add `gunicorn` to `requirements.txt` before deploying if you use that start command. For persistent data/uploads on Render, configure a persistent disk or use a database/object storage; the default local filesystem may not persist across redeploys.
