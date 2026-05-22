from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3, os

app = Flask(__name__)
app.secret_key = "leadradar-secret"
DB = os.path.join(os.path.dirname(__file__), "leadradar.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            weight INTEGER DEFAULT 3,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER REFERENCES groups(id),
            sender TEXT,
            content TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            read INTEGER DEFAULT 0,
            archived INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

init_db()
THRESHOLD = 3

def score_message(content, keywords):
    """Score a message against keyword list. Returns total weighted score."""
    score = 0
    content_lower = content.lower()
    for kw in keywords:
        if kw["word"].lower() in content_lower:
            score += kw["weight"]
    return score

@app.route("/")
def index():
    conn = get_db()
    stats = {
        "groups":        conn.execute("SELECT COUNT(*) FROM groups").fetchone()[0],
        "keywords":      conn.execute("SELECT COUNT(*) FROM keywords").fetchone()[0],
        "opportunities": conn.execute("SELECT COUNT(*) FROM messages WHERE score >= ? AND archived=0", (THRESHOLD,)).fetchone()[0],
        "unread":        conn.execute("SELECT COUNT(*) FROM messages WHERE score >= ? AND read=0 AND archived=0", (THRESHOLD,)).fetchone()[0],
    }
    recent = conn.execute("""
        SELECT m.*, g.name as group_name FROM messages m
        LEFT JOIN groups g ON m.group_id = g.id
        WHERE m.score >= ? AND m.archived=0
        ORDER BY m.created_at DESC LIMIT 5
    """, (THRESHOLD,)).fetchall()
    return render_template("index.html", stats=stats, recent=recent)

@app.route("/groups", methods=["GET", "POST"])
def groups():
    conn = get_db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            name = request.form.get("name", "").strip()
            desc = request.form.get("description", "").strip()
            if not name:
                flash("Group name is required.", "error")
            else:
                conn.execute("INSERT INTO groups(name, description) VALUES(?, ?)", (name, desc))
                conn.commit()
                flash(f'Group "{name}" added.', "success")
        elif action == "delete":
            gid = request.form.get("gid")
            conn.execute("DELETE FROM groups WHERE id=?", (gid,))
            conn.execute("DELETE FROM messages WHERE group_id=?", (gid,))
            conn.commit()
            flash("Group deleted.", "success")
        return redirect(url_for("groups"))
    all_groups = conn.execute("SELECT * FROM groups ORDER BY created_at DESC").fetchall()
    return render_template("groups.html", groups=all_groups)

@app.route("/keywords", methods=["GET", "POST"])
def keywords():
    conn = get_db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            word = request.form.get("word", "").strip()
            weight = int(request.form.get("weight", 3))
            if not word:
                flash("Keyword cannot be empty.", "error")
            else:
                # Edge case: prevent case-insensitive duplicates
                existing = conn.execute(
                    "SELECT id FROM keywords WHERE LOWER(word)=LOWER(?)", (word,)
                ).fetchone()
                if existing:
                    flash(f'"{word}" already exists.', "error")
                else:
                    conn.execute("INSERT INTO keywords(word, weight) VALUES(?, ?)", (word, weight))
                    conn.commit()
                    flash(f'Keyword "{word}" added.', "success")
        elif action == "delete":
            kid = request.form.get("kid")
            conn.execute("DELETE FROM keywords WHERE id=?", (kid,))
            conn.commit()
            flash("Keyword removed.", "success")
        return redirect(url_for("keywords"))
    all_kw = conn.execute("SELECT * FROM keywords ORDER BY weight DESC, word ASC").fetchall()
    return render_template("keywords.html", keywords=all_kw)

@app.route("/scan", methods=["GET", "POST"])
def scan():
    conn = get_db()
    result = None
    if request.method == "POST":
        content  = request.form.get("content", "").strip()
        sender   = request.form.get("sender", "").strip()
        group_id = request.form.get("group_id") or None
        if not content:
            flash("Message content is required.", "error")
        else:
            kws     = conn.execute("SELECT * FROM keywords").fetchall()
            score   = score_message(content, kws)
            matched = [kw["word"] for kw in kws if kw["word"].lower() in content.lower()]
            if score >= THRESHOLD:
                conn.execute(
                    "INSERT INTO messages(group_id, sender, content, score) VALUES(?,?,?,?)",
                    (group_id, sender, content, score)
                )
                conn.commit()
                flash(f"Opportunity saved! Score: {score}", "success")
            else:
                flash(f"Score {score} — below threshold ({THRESHOLD}). Not saved.", "info")
            result = {"score": score, "matched": matched, "threshold": THRESHOLD, "saved": score >= THRESHOLD}
    all_groups = conn.execute("SELECT * FROM groups ORDER BY name").fetchall()
    return render_template("scan.html", result=result, groups=all_groups)

@app.route("/opportunities")
def opportunities():
    conn = get_db()
    filter_by = request.args.get("filter", "active")
    if filter_by == "archived":
        where = "m.score >= ? AND m.archived=1"
    elif filter_by == "all":
        where = "m.score >= ?"
    else:
        where = "m.score >= ? AND m.archived=0"
    msgs = conn.execute(f"""
        SELECT m.*, g.name as group_name FROM messages m
        LEFT JOIN groups g ON m.group_id = g.id
        WHERE {where}
        ORDER BY m.read ASC, m.created_at DESC
    """, (THRESHOLD,)).fetchall()
    return render_template("opportunities.html", messages=msgs, filter=filter_by)

@app.route("/messages/read/<int:mid>", methods=["POST"])
def mark_read(mid):
    conn = get_db()
    conn.execute("UPDATE messages SET read=1 WHERE id=?", (mid,))
    conn.commit()
    return redirect(request.referrer or url_for("opportunities"))

@app.route("/messages/archive/<int:mid>", methods=["POST"])
def archive_msg(mid):
    conn = get_db()
    conn.execute("UPDATE messages SET archived=1 WHERE id=?", (mid,))
    conn.commit()
    return redirect(request.referrer or url_for("opportunities"))

@app.route("/messages/delete/<int:mid>", methods=["POST"])
def delete_msg(mid):
    conn = get_db()
    conn.execute("DELETE FROM messages WHERE id=?", (mid,))
    conn.commit()
    flash("Message deleted.", "success")
    return redirect(request.referrer or url_for("opportunities"))

if __name__ == "__main__":
    app.run(debug=True)
    
