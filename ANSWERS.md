# ANSWERS.md

## 1. How to Run

```bash
pip install flask
python app.py
```

Open http://127.0.0.1:5000. No other setup needed.
SQLite DB (`leadradar.db`) is auto-created on first run.

## 2. Stack Choice

**Flask + SQLite + Jinja2.**

Flask was the right choice because the entire app lives in one file with zero
scaffolding. SQLite via Python's built-in `sqlite3` module means the only
install required is `flask` itself — no database server, no migrations, no
config files. Setup is a single command on any machine.

A worse choice would have been Django: it requires `settings.py`,
`INSTALLED_APPS`, `migrations`, and a management command just to reach hello
world. For a self-contained tool a reviewer should run in 30 seconds, that
overhead is unnecessary and hostile to the "fresh machine" requirement.

## 3. One Real Edge Case

**Case-insensitive duplicate keyword prevention**

File: `app.py`, in the `/keywords` POST handler:

```python
existing = conn.execute(
    "SELECT id FROM keywords WHERE LOWER(word)=LOWER(?)", (word,)
).fetchone()
if existing:
    flash(f'"{word}" already exists.', "error")
else:
    conn.execute("INSERT INTO keywords(word, weight) VALUES(?, ?)", (word, weight))
```

Without this check, a user could add "Django" and "django" as separate keywords.
Both would match every message containing the word, doubling the score and
causing messages to be falsely flagged as high-priority opportunities.
The `LOWER()` comparison catches this regardless of how the user typed it.

## 4. AI Usage

Used Perplexity AI to scaffold the initial Flask routes, SQLite schema, and
all HTML templates.

**What I changed:**
- The initial scoring function used `word in content`. I changed it to
  `word.lower() in content.lower()` so "Django" matches "django", "DJANGO",
  etc. Without this the radar silently misses a large portion of real messages.
- Raised the default flagging threshold from 2 to 3 after testing showed too
  many false positives — a single weak keyword alone shouldn't trigger a save.
- Added the matched keyword list in the scan result so the user can see *why*
  a message was flagged, not just that it scored high.

## 5. Honest Gap

The biggest gap is that messages must be pasted manually. The real vision is
automatic monitoring — watching WhatsApp Web in real time without any
copy-paste step from the user.

With another day I would build a Selenium-based watcher that opens WhatsApp
Web, polls each configured group every 60 seconds, extracts new messages, and
POSTs them to an internal `/api/scan` endpoint. The scoring and storage logic
is already complete — the manual Scan page is a working prototype of that
automated pipeline. The core is done; only the ingestion layer is missing.
