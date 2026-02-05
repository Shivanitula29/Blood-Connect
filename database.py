import sqlite3

def create_db():
    conn = sqlite3.connect('blood.db')
    cur = conn.cursor()

    # Donor Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS donors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        blood TEXT,
        phone TEXT,
        location TEXT,
        last_donated TEXT
    )
    ''')

    # Request Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient TEXT,
        blood TEXT,
        hospital TEXT,
        location TEXT,
        status TEXT
    )
    ''')

    conn.commit()
    conn.close()

create_db()
