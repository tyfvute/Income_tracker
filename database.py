import sqlite3

DB_NAME = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    queries = [
        "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)",
        "CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY, user_id INTEGER, amount INTEGER, category TEXT, type TEXT, date TEXT)",
        "CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY, user_id INTEGER, target INTEGER, description TEXT)",
        "INSERT OR IGNORE INTO users (username, password) VALUES ('1', '1')"
    ]
    for q in queries: conn.execute(q)
    conn.commit()
    conn.close()
