import sqlite3
from datetime import datetime


connection = sqlite3.connect("bot.db")
cursor = connection.cursor()


# =========================
# APPLICATIONS
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    task TEXT NOT NULL,
    phone TEXT NOT NULL,
    date TEXT,
    time TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    telegram_id INTEGER
)
""")
connection.commit()


# Миграция: добавляем status
try:
    cursor.execute(
        "ALTER TABLE applications ADD COLUMN status TEXT NOT NULL DEFAULT 'new'"
    )
    connection.commit()
except sqlite3.OperationalError:
    pass


# Миграция: добавляем telegram_id
try:
    cursor.execute(
        "ALTER TABLE applications ADD COLUMN telegram_id INTEGER"
    )
    connection.commit()
except sqlite3.OperationalError:
    pass


# Миграция: добавляем date
try:
    cursor.execute(
        "ALTER TABLE applications ADD COLUMN date TEXT"
    )
    connection.commit()
except sqlite3.OperationalError:
    pass


# Миграция: добавляем time
try:
    cursor.execute(
        "ALTER TABLE applications ADD COLUMN time TEXT"
    )
    connection.commit()
except sqlite3.OperationalError:
    pass


# =========================
# SCHEDULE
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'available',
    telegram_id INTEGER,
    UNIQUE(date, time)
)
""")
connection.commit()


# Миграция для старой таблицы schedule
try:
    cursor.execute(
        "ALTER TABLE schedule ADD COLUMN telegram_id INTEGER"
    )
    connection.commit()
except sqlite3.OperationalError:
    pass


# =========================
# APPLICATION FUNCTIONS
# =========================

def save_application(name, task, date, time, phone, telegram_id):
    cursor.execute(
        """
        INSERT INTO applications (
            name,
            task,
            date,
            time,
            phone,
            telegram_id
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            task,
            date,
            time,
            phone,
            telegram_id
        )
    )

    connection.commit()

    return cursor.lastrowid


def get_applications():
    cursor.execute(
        """
        SELECT id, name, task, phone, status
        FROM applications
        ORDER BY id DESC
        """
    )

    return cursor.fetchall()


def get_application(application_id):
    cursor.execute(
        """
        SELECT
            id,
            name,
            task,
            date,
            time,
            phone,
            status,
            telegram_id
        FROM applications
        WHERE id = ?
        """,
        (application_id,)
    )

    return cursor.fetchone()


def delete_application(application_id):
    # Получаем данные заявки перед удалением,
    # чтобы освободить соответствующий слот.
    cursor.execute(
        """
        SELECT date, time, telegram_id
        FROM applications
        WHERE id = ?
        """,
        (application_id,)
    )

    application = cursor.fetchone()

    if application:
        application_date, application_time, telegram_id = application

        # Освобождаем слот.
        cursor.execute(
            """
            UPDATE schedule
            SET
                status = 'available',
                telegram_id = NULL
            WHERE date = ?
              AND time = ?
              AND status = 'booked'
              AND telegram_id = ?
            """,
            (
                application_date,
                application_time,
                telegram_id
            )
        )

    # Удаляем заявку.
    cursor.execute(
        """
        DELETE FROM applications
        WHERE id = ?
        """,
        (application_id,)
    )

    connection.commit()


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
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'new' THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed
        FROM applications
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    )

    result = cursor.fetchone()

    total = result[0] or 0
    active = result[1] or 0
    completed = result[2] or 0

    return total, active, completed


def get_user_applications(telegram_id):
    cursor.execute(
        """
        SELECT
            id,
            task,
            date,
            time,
            status
        FROM applications
        WHERE telegram_id = ?
        ORDER BY id DESC
        """,
        (telegram_id,)
    )

    return cursor.fetchall()


def cancel_application(application_id, telegram_id):
    # Получаем дату и время заявки.
    cursor.execute(
        """
        SELECT date, time
        FROM applications
        WHERE id = ?
          AND telegram_id = ?
          AND status = 'new'
        """,
        (
            application_id,
            telegram_id
        )
    )

    application = cursor.fetchone()

    if not application:
        return False

    application_date, application_time = application

    # Освобождаем слот.
    cursor.execute(
        """
        UPDATE schedule
        SET
            status = 'available',
            telegram_id = NULL
        WHERE date = ?
          AND time = ?
          AND status = 'booked'
          AND telegram_id = ?
        """,
        (
            application_date,
            application_time,
            telegram_id
        )
    )

    # Удаляем заявку.
    cursor.execute(
        """
        DELETE FROM applications
        WHERE id = ?
          AND telegram_id = ?
          AND status = 'new'
        """,
        (
            application_id,
            telegram_id
        )
    )

    connection.commit()

    return cursor.rowcount > 0


# =========================
# SCHEDULE CLEANUP
# =========================

def delete_expired_schedule_slots():
    """
    Удаляет все слоты, дата и время которых уже прошли.
    Формат даты: DD.MM.YYYY
    Формат времени: HH:MM
    """

    now = datetime.now()

    cursor.execute(
        """
        SELECT id, date, time
        FROM schedule
        """
    )

    slots = cursor.fetchall()

    expired_ids = []

    for slot_id, slot_date, slot_time in slots:
        try:
            slot_datetime = datetime.strptime(
                f"{slot_date} {slot_time}",
                "%d.%m.%Y %H:%M"
            )

            if slot_datetime < now:
                expired_ids.append(slot_id)

        except (ValueError, TypeError):
            continue

    for slot_id in expired_ids:
        cursor.execute(
            """
            DELETE FROM schedule
            WHERE id = ?
            """,
            (slot_id,)
        )

    connection.commit()


# =========================
# SCHEDULE FUNCTIONS
# =========================

def add_schedule_slot(date, time):
    cursor.execute(
        """
        SELECT id, status
        FROM schedule
        WHERE date = ?
          AND time = ?
        """,
        (
            date,
            time
        )
    )

    existing_slot = cursor.fetchone()

    if existing_slot:
        return False

    cursor.execute(
        """
        INSERT INTO schedule (
            date,
            time,
            status,
            telegram_id
        )
        VALUES (?, ?, 'available', NULL)
        """,
        (
            date,
            time
        )
    )

    connection.commit()

    return cursor.lastrowid


def get_schedule():
    delete_expired_schedule_slots()

    cursor.execute(
        """
        SELECT
            id,
            date,
            time,
            status,
            telegram_id
        FROM schedule
        ORDER BY
            substr(date, 7, 4),
            substr(date, 4, 2),
            substr(date, 1, 2),
            time
        """
    )

    return cursor.fetchall()

def get_schedule_by_date(date):
    delete_expired_schedule_slots()

    cursor.execute(
        """
        SELECT
            id,
            date,
            time,
            status,
            telegram_id
        FROM schedule
        WHERE date = ?
        ORDER BY time
        """,
        (date,)
    )

    return cursor.fetchall()


def get_schedule_slot(slot_id):
    delete_expired_schedule_slots()

    cursor.execute(
        """
        SELECT
            id,
            date,
            time,
            status,
            telegram_id
        FROM schedule
        WHERE id = ?
        """,
        (slot_id,)
    )

    return cursor.fetchone()


def get_available_schedule():
    delete_expired_schedule_slots()

    cursor.execute(
        """
        SELECT
            id,
            date,
            time,
            status,
            telegram_id
        FROM schedule
        WHERE status = 'available'
        ORDER BY
            substr(date, 7, 4),
            substr(date, 4, 2),
            substr(date, 1, 2),
            time
        """
    )

    return cursor.fetchall()


def get_available_schedule_by_date(date):
    delete_expired_schedule_slots()

    cursor.execute(
        """
        SELECT
            id,
            date,
            time,
            status,
            telegram_id
        FROM schedule
        WHERE date = ?
          AND status = 'available'
        ORDER BY time
        """,
        (date,)
    )

    return cursor.fetchall()


def book_schedule_slot(slot_id, telegram_id):
    cursor.execute(
        """
        UPDATE schedule
        SET
            status = 'booked',
            telegram_id = ?
        WHERE id = ?
          AND status = 'available'
        """,
        (
            telegram_id,
            slot_id
        )
    )

    connection.commit()

    return cursor.rowcount > 0


def release_schedule_slot(slot_id):
    cursor.execute(
        """
        UPDATE schedule
        SET
            status = 'available',
            telegram_id = NULL
        WHERE id = ?
        """,
        (slot_id,)
    )

    connection.commit()


def delete_schedule_slot(slot_id):
    cursor.execute(
        """
        DELETE FROM schedule
        WHERE id = ?
        """,
        (slot_id,)
    )

    connection.commit()