import sqlite3

connection = sqlite3.connect("bot.db")
cursor = connection.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    task TEXT NOT NULL,
    phone TEXT NOT NULL
)
""")

connection.commit()

try:
    cursor.execute(
        "ALTER TABLE applications ADD COLUMN status TEXT NOT NULL DEFAULT 'new'"
    )
    connection.commit()
except sqlite3.OperationalError:
    pass

def save_application(name, task, phone):
    cursor.execute(
        "INSERT INTO applications (name, task, phone) VALUES (?, ?, ?)",
        (name, task, phone)
    )

    connection.commit()

def get_applications():
    cursor.execute(
        "SELECT id, name, task, phone, status FROM applications"
    )
    return cursor.fetchall()


def get_application(application_id):
    cursor.execute(
        "SELECT id, name, task, phone, status FROM applications WHERE id = ?",
        (application_id,)
    )

    return cursor.fetchone()
    return cursor.fetchone()

def delete_application(application_id):
    cursor.execute(
        "DELETE FROM applications WHERE id = ?",
        (application_id,)
    )

    connection.commit()

def complete_application(application_id):
    cursor.execute(
        "UPDATE applications SET status = 'completed' WHERE id = ?",
        (application_id,)
    )

    connection.commit()

def reopen_application(application_id):
    cursor.execute(
        "UPDATE applications SET status = 'new' WHERE id = ?",
        (application_id,)
    )
    connection.commit()