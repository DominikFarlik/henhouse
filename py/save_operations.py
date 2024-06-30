import logging
import sqlite3
import threading
import time

from config import read_config

import requests  # type: ignore
import datetime
from requests.auth import HTTPBasicAuth  # type: ignore

config = read_config()

DB_PATH = config.get('DB', 'file_path')

RESEND_TIMER = 600

# api constants
username = config.get('API', 'username')
password = config.get('API', 'password')
time_zone_offset = config.getint('API', 'timezone_offset')


def save_record(chip_id: int, reader_id: str, event_time: datetime, event_type: int) -> None:
    record_id = write_event_to_db(chip_id, reader_id, event_time, event_type)
    in_api = create_api_record(record_id, event_time, chip_id, event_type, reader_id)
    if in_api == 1:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE events SET in_api = 1 WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()


def compare_api_db_id():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM events")
    last_db_id = cursor.fetchone()
    last_db_id = last_db_id[0]
    conn.close()

    if get_starting_id_from_api() == last_db_id:
        logging.info("Last api and db ids are matching.")


def resend_failed_records():
    while True:
        print("xxx")
        records_to_resend = fetch_failed_api_records()

        for record in records_to_resend:
            print(record)
            in_api = create_api_record(record[0], record[2], record[1], record[4], record[3])
            if in_api == 1:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("UPDATE events SET in_api = 1 WHERE id = ?", (record[0],))
                conn.commit()
                conn.close()
        time.sleep(RESEND_TIMER)


# db operations
def write_event_to_db(chip_id: int, reader_id: str, event_time: str, event_type: int) -> int:
    """Writes received data to the database."""
    lock = threading.Lock()
    with lock:
        try:
            with sqlite3.connect(DB_PATH) as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "INSERT INTO events (chip_id, reader_id, event_type, event_time) VALUES (?, ?, ?, ?)",
                    (chip_id, reader_id, event_type, event_time),
                )
                connection.commit()
                return cursor.lastrowid

        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")


# api operations
def fetch_failed_api_records():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE in_api = 0 LIMIT 5")
    records = cursor.fetchall()
    conn.close()
    return records


def create_api_record(record_id: int, time: str, rfid: int, record_type: int, reader_id: str) -> int:
    params = {
        "TerminalTime": time,
        "TerminalTimeZone": time_zone_offset,
        "IsImmediate": False,
        "TimeAttendanceRecords": [
            {
                "RecordId": record_id,
                "RecordType": record_type,
                "RFID": rfid,
                "Punched": datetime.datetime.now().isoformat(),
                "HWSource": reader_id[-1]
            }
        ]
    }

    try:
        response = requests.post('https://itaserver-staging.mobatime.cloud/api/TimeAttendance',
                                 json=params,
                                 auth=HTTPBasicAuth(username, password))
        response.raise_for_status()  # Ensure we raise an error for bad responses
        logging.info(f"Successfully created API record with ID: {record_id}")
        return 1

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to create API record: {e}")
        if "Terminal_TimeOfTheTerminalIsNotSetCorrectly" in str(e) or "Records_RecordAlreadyExists" in str(e):
            logging.info(f"Handled error: {e}. Record ID: {record_id} considered delivered.")
            return 1
        else:
            return 0


def get_starting_id_from_api() -> int:
    try:
        response = requests.get('https://itaserver-staging.mobatime.cloud/api/TimeAttendanceRecordId',
                                auth=HTTPBasicAuth(username, password))
        response.raise_for_status()  # Ensure we raise an error for bad responses
        data = response.json()
        logging.info(f"Retrieved last record ID from api: {data['LastTimeAttendanceRecordId']}")
        return data['LastTimeAttendanceRecordId']
    except requests.RequestException as e:
        logging.error(f"Failed to get last ID from API: {e}")
        raise
