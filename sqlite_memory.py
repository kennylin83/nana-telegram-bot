import sqlite3, os, json

DB_PATH = "data/memory.db"

def get_conn():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            user_id TEXT PRIMARY KEY,
            content TEXT
        )
    ''')
    conn.commit()
    conn.close()

def load_memory(user_id):
    init_db()
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT content FROM memories WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return []

def save_memory(user_id, history):
    init_db()
    conn = get_conn()
    c = conn.cursor()
    c.execute("REPLACE INTO memories (user_id, content) VALUES (?, ?)", (user_id, json.dumps(history)))
    conn.commit()
    conn.close()

def reset_memory(user_id):
    init_db()
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM memories WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def is_authorized(update):
    return True  # 可根據需要限制特定用戶
