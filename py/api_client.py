import logging
import requests  # type: ignore
import datetime
from requests.auth import HTTPBasicAuth  # type: ignore


class APIClient:
    def __init__(self, username: str, password: str, time_zone_offset: int):
        self.username = username
        self.password = password
        self.time_zone_offset = time_zone_offset
        self.record_id = self.get_starting_id_for_api()

    def get_starting_id_for_api(self) -> int:
        try:
            response = requests.get('https://itaserver-staging.mobatime.cloud/api/TimeAttendanceRecordId',
                                    auth=HTTPBasicAuth(self.username, self.password))
            response.raise_for_status()  # Ensure we raise an error for bad responses
            data = response.json()
            logging.info(f"Retrieved starting record ID: {data['LastTimeAttendanceRecordId'] + 1}")
            return data['LastTimeAttendanceRecordId'] + 1
        except requests.RequestException as e:
            logging.error(f"Failed to get starting ID from API: {e}")
            raise

    def create_api_record(self, time: str, rfid: int, record_type: int, reader_id: str) -> int:
        params = {
            "TerminalTime": time,
            "TerminalTimeZone": self.time_zone_offset,
            "IsImmediate": False,
            "TimeAttendanceRecords": [
                {
                    "RecordId": self.record_id,
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
                                     auth=HTTPBasicAuth(self.username, self.password))
            response.raise_for_status()  # Ensure we raise an error for bad responses
            logging.info(f"Successfully created API record with ID: {self.record_id}")
            self.record_id += 1  # Increment the record ID after a successful post
            return 1
        except requests.RequestException as e:
            logging.error(f"Failed to create API record: {e}")
            return 0
