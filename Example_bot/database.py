import sqlite3


connection = sqlite3.connect("bot.db")
cursor = connection.cursor()


# =========================
# Создание таблицы
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    task TEXT NOT NULL,
    phone TEXT NOT NULL
)
""")

connection.commit()


# =========================
# Добавление новых колонок
# =========================

try:
    cursor.execute(
        "ALTER TABLE applications ADD COLUMN status TEXT NOT NULL DEFAULT 'new'"
    )
    connection.commit()
except sqlite3.OperationalError:
    pass


try:
    cursor.execute(
        "ALTER TABLE applications ADD COLUMN telegram_id INTEGER"
    )
    connection.commit()
except sqlite3.OperationalError:
    pass


# =========================
# Сохранение заявки
# =========================

def save_application(name, task, phone, telegram_id):
    cursor.execute(
        """
        INSERT INTO applications (
            name,
            task,
            phone,
            telegram_id
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            name,
            task,
            phone,
            telegram_id
        )
    )

    connection.commit()

    return cursor.lastrowid


# =========================
# Получить все заявки
# =========================

def get_applications():
    cursor.execute(
        """
        SELECT
            id,
            name,
            task,
            phone,
            status,
            telegram_id
        FROM applications
        """
    )

    return cursor.fetchall()


# =========================
# Получить одну заявку
# =========================

def get_application(application_id):
    cursor.execute(
        """
        SELECT
            id,
            name,
            task,
            phone,
            status,
            telegram_id
        FROM applications
        WHERE id = ?
        """,
        (application_id,)
    )

    return cursor.fetchone()


# =========================
# Удалить заявку
# =========================

def delete_application(application_id):
    cursor.execute(
        "DELETE FROM applications WHERE id = ?",
        (application_id,)
    )

    connection.commit()


# =========================
# Выполнить заявку
# =========================

def complete_application(application_id):
    cursor.execute(
        """
        UPDATE applications
        SET status = 'completed'
        WHERE id = ?
        """,
        (application_id,)
    )

    connection.commit()


# =========================
# Вернуть заявку в работу
# =========================

def reopen_application(application_id):
    cursor.execute(
        """
        UPDATE applications
        SET status = 'new'
        WHERE id = ?
        """,
        (application_id,)
    )

    connection.commit()

def get_user_application_stats(telegram_id):
    cursor.execute(
        """
        SELECT
            COUNT(*),
            SUM(CASE WHEN status = 'new' THEN 1 ELSE 0 END),
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END)
        FROM applications
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    )

    result = cursor.fetchone()

    total = result[0] or 0
    new = result[1] or 0
    completed = result[2] or 0

    return total, new, completed

def get_user_applications(telegram_id):
    cursor.execute(
        """
        SELECT id, task, status
        FROM applications
        WHERE telegram_id = ?
        ORDER BY id DESC
        """,
        (telegram_id,)
    )

    return cursor.fetchall()


def cancel_application(application_id, telegram_id):
    cursor.execute(
        """
        UPDATE applications
        SET status = 'cancelled'
        WHERE id = ?
        AND telegram_id = ?
        AND status = 'new'
        """,
        (application_id, telegram_id)
    )

    connection.commit()

    return cursor.rowcount > 0