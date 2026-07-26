import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "yt_analyzer.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id TEXT PRIMARY KEY,
            user_email TEXT NOT NULL,
            title TEXT,
            description TEXT,
            thumbnail TEXT,
            channel TEXT,
            published_at TEXT,
            category TEXT DEFAULT 'Diğer',
            summary TEXT,
            liked_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            video_id TEXT,
            video_title TEXT,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def save_videos(user_email, videos):
    conn = get_db()
    c = conn.cursor()
    for v in videos:
        c.execute("""
            INSERT OR REPLACE INTO videos
            (id, user_email, title, description, thumbnail, channel, published_at, liked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            v["id"], user_email, v["title"], v["description"],
            v["thumbnail"], v["channel"], v["published_at"], v.get("liked_at", "")
        ))
    conn.commit()
    conn.close()


def get_videos(user_email, category=None, search=None):
    conn = get_db()
    c = conn.cursor()
    query = "SELECT * FROM videos WHERE user_email = ?"
    params = [user_email]
    if category and category != "Tümü":
        query += " AND category = ?"
        params.append(category)
    if search:
        query += " AND (title LIKE ? OR channel LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    query += " ORDER BY liked_at DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_video(video_id, user_email):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM videos WHERE id = ? AND user_email = ?", (video_id, user_email))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def update_video_category(video_id, user_email, category):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE videos SET category = ? WHERE id = ? AND user_email = ?",
              (category, video_id, user_email))
    conn.commit()
    conn.close()


def update_video_summary(video_id, user_email, summary):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE videos SET summary = ? WHERE id = ? AND user_email = ?",
              (summary, video_id, user_email))
    conn.commit()
    conn.close()


def get_category_stats(user_email):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT category, COUNT(*) as count
        FROM videos WHERE user_email = ?
        GROUP BY category ORDER BY count DESC
    """, (user_email,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_note(user_email, content, video_id=None, video_title=None):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO notes (user_email, video_id, video_title, content)
        VALUES (?, ?, ?, ?)
    """, (user_email, video_id, video_title, content))
    note_id = c.lastrowid
    conn.commit()
    conn.close()
    return note_id


def get_notes(user_email):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM notes WHERE user_email = ? ORDER BY created_at DESC", (user_email,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_note(note_id, user_email):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM notes WHERE id = ? AND user_email = ?", (note_id, user_email))
    conn.commit()
    conn.close()


def update_note(note_id, user_email, content):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        UPDATE notes SET content = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_email = ?
    """, (content, note_id, user_email))
    conn.commit()
    conn.close()


def count_videos(user_email):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM videos WHERE user_email = ?", (user_email,))
    count = c.fetchone()[0]
    conn.close()
    return count

def save_user_api_key(user_email, api_key):
    """Kullanıcının kendi özel API anahtarını kaydeder."""
    conn = get_db()
    c = conn.cursor()
    # Tabloda sütun yoksa ekle
    try:
        c.execute("ALTER TABLE users ADD COLUMN api_key TEXT")
    except Exception:
        pass
    c.execute("UPDATE users SET api_key = ? WHERE email = ?", (api_key, user_email))
    conn.commit()
    conn.close()

def get_user_api_key(user_email):
    """Kullanıcının özel API anahtarını getirir."""
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("SELECT api_key FROM users WHERE email = ?", (user_email,))
        row = c.fetchone()
        conn.close()
        return row["api_key"] if row and row["api_key"] else None
    except Exception:
        conn.close()
        return None