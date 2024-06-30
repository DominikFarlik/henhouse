import logging
import sqlite3
import threading
from config import read_config

config = read_config()

DB_PATH = config.get('DB', 'file_path')


def write_event_to_db(
        chip_id: int, reader_id: str, event_time: str, event_type: int, in_api: int
) -> None:
    """Writes received data to the database."""
    lock = threading.Lock()
    with lock:
        try:
            with sqlite3.connect(DB_PATH) as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO events (chip_id, reader_id, event_type, event_time, in_api) VALUES (?, ?, ?, ?, ?)",
                    (chip_id, reader_id, event_type, event_time, in_api),
                )
                connection.commit()
                #  logging.info(f"Event written to DB: {chip_id}, {reader_id}, {event_type}, {event_time}")
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")


def fetch_failed_api_records():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE in_api = 1 LIMIT 5")
    records = cursor.fetchall()
    conn.close()
    print(records)
    return records
