# LeadRadar

A persistent web app that monitors WhatsApp community messages and flags
potential opportunities based on your custom keyword profile.

## Requirements
- Python 3.8+

## Setup & Run

```bash
pip install flask
python app.py
```

Open http://127.0.0.1:5000 in your browser.
SQLite database (`leadradar.db`) is created automatically on first run.

## How to Use

1. **Groups** — Add the WhatsApp groups you monitor
2. **Keywords** — Add keywords with weights (e.g. "need a developer" weight 5)
3. **Scan** — Paste a message and click Scan. Score >= 3 saves it as an opportunity
4. **Opportunities** — View, mark read, archive, or delete flagged messages

## Features
- Full CRUD for groups and keywords
- Weighted keyword scoring engine
- Persistent SQLite storage (survives restarts)
- Dark / light mode toggle
- Filter opportunities: Active / Archived / All
