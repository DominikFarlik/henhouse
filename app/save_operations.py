import logging
import sqlite3
import threading
import time

from .config import read_config

import requests  # type: ignore
import datetime
from requests.auth import HTTPBasicAuth  # type: ignore

config = read_config()

DB_PATH = config.get('DB', 'file_path')

RESEND_TIMER = 1800

FAIL_LIMIT = 10

# api constants
username = config.get('API', 'username')
password = config.get('API', 'password')
time_zone_offset = config.getint('API', 'timezone_offset')
url = config.get('API', 'url')


def save_record(chip_id: int, reader_id: int, event_time: str, event_type: int) -> None:
    """Saves record to database, then try to send to api and check if it was successful"""
    record_id = write_event_to_db(chip_id, reader_id, event_time, event_type)
    in_api = create_api_record(record_id, event_time, chip_id, event_type, reader_id)
    if in_api == 1:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE events SET in_api = 1 WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()


def compare_api_db_id():
    """Debug function to check if last id in database is equal to last id in api"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM events")
    last_db_id = cursor.fetchone()
    last_db_id = last_db_id[0]
    conn.close()
    starting_api_id = get_starting_id_from_api()

    if starting_api_id == last_db_id:
        logging.info("Last api and db ids are matching.")
    elif starting_api_id < last_db_id:
        pass  # there should be check if data with lower ids are in db and just not sent to api
    else:
        logging.warning("Last api and db ids are not matching! Synchronizing...")
        sync_db_with_api(starting_api_id)


def resend_failed_records():
    """Repeatedly sends failed records to api till its successful or FAIL_LIMIT"""
    while True:
        records_to_resend = fetch_failed_api_records()

        for record in records_to_resend:
            record_id = record[0]
            rfid = record[1]
            event_time = record[2]
            reader_id = record[3]
            record_type = record[4]

            in_api = create_api_record(record_id, event_time, rfid, record_type, reader_id)
            if in_api == 1:
                make_record_sent(record_id)
            else:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("UPDATE events SET api_attempts = api_attempts + 1 WHERE id = ?", (record_id,))
                conn.commit()

                cursor.execute("SELECT api_attempts FROM events WHERE id = ?", (record[0],))
                api_attempts = cursor.fetchone()[0]
                conn.close()

                if api_attempts >= FAIL_LIMIT:
                    send_to_error_endpoint(record_id, event_time, rfid, record_type, reader_id)
                    make_record_sent(record_id)

        time.sleep(RESEND_TIMER)


# db operations
def write_event_to_db(chip_id: int, reader_id: int, event_time: str, event_type: int) -> int:
    """Writes received data to the database."""
    lock = threading.Lock()
    with lock:
        with sqlite3.connect(DB_PATH) as connection:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO events (chip_id, reader_id, event_type, event_time) VALUES (?, ?, ?, ?)",
                (chip_id, reader_id, event_type, event_time),
            )
            connection.commit()
            return cursor.lastrowid


def get_number_of_unsent_records():
    """Returns the number of unsent records in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM events WHERE in_api = 0")
    data = cursor.fetchone()
    number_of_unsent_records = data[0]
    conn.close()
    return number_of_unsent_records


def fetch_failed_api_records():
    """Returns the list of 5 failed records"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE in_api = 0 LIMIT 5")
    records = cursor.fetchall()
    conn.close()
    return records


def database_initialization():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chip_id INTEGER NOT NULL,
            event_time TIMESTAMP,
            reader_id TEXT NOT NULL,
            event_type INTEGER NOT NULL,
            in_api INTEGER NOT NULL DEFAULT 0,
            api_attempts INTEGER DEFAULT 1)
            """)
    connection.close()


def sync_db_with_api(starting_id: int) -> None:
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO events (id, chip_id, reader_id, event_type, in_api) VALUES (?, ?, ?, ?, ?)",
        (starting_id, 0, "None", 0, 1),
    )
    connection.commit()
    connection.close()


# api operations
def create_api_record(record_id: int, event_time: str, rfid: int, record_type: int, reader_id: int) -> int:
    """Sending new time attendance record to api"""
    params = {
        "TerminalTime": event_time,
        "TerminalTimeZone": time_zone_offset,
        "IsImmediate": False,
        "TimeAttendanceRecords": [
            {
                "RecordId": record_id,
                "RecordType": record_type,
                "RFID": rfid,
                "Punched": datetime.datetime.now().isoformat(),
                "HWSource": reader_id
            }
        ]
    }

    try:
        response = requests.post(f'{url}/api/TimeAttendance',
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
    """Get last id from api"""
    try:
        response = requests.get(f'{url}/api/TimeAttendanceRecordId',
                                auth=HTTPBasicAuth(username, password))
        response.raise_for_status()  # Ensure we raise an error for bad responses
        data = response.json()
        logging.info(f"Retrieved last record ID from api: {data['LastTimeAttendanceRecordId']}")
        return data['LastTimeAttendanceRecordId']
    except requests.RequestException as e:
        logging.error(f"Failed to get last ID from API: {e}")
        raise


def make_record_sent(record_id: int) -> None:
    """Update in_api var in db to 1(successful)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE events SET in_api = 1 WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


def send_to_error_endpoint(record_id: int, event_time: str, rfid: int, record_type: int, reader_id: str):
    """After many failed sent records, send them to error endpoint."""
    params = {
        "TerminalTime": event_time,
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
        response = requests.post(f'{url}/api/ErrorReporting',
                                 json=params,
                                 auth=HTTPBasicAuth(username, password))

        response.raise_for_status()

    except requests.RequestException as e:
        logging.error(f"Failed to sent record to error endpoint: {e}")
