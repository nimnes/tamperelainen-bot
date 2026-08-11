import sqlite3
from config import DB_PATH

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS articles ("
            "url TEXT PRIMARY KEY, title TEXT NOT NULL, published TEXT, "
            "processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        conn.commit()

def is_processed(url):
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(
            "SELECT 1 FROM articles WHERE url=? LIMIT 1", (url,)
        ).fetchone() is not None

def mark_processed(url, title, published=""):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO articles(url,title,published) VALUES(?,?,?)",
            (url, title, published)
        )
        conn.commit()


def any_processed():
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(
            "SELECT 1 FROM articles LIMIT 1"
        ).fetchone() is not None
