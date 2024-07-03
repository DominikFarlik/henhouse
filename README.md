# Henhouse

### 1. Clone git repository
`git clone git@github.com:DominikFarlik/henhouse.git`
### 2. Move into project directory
`cd henhouse`
### 3. Create and activate virtual env
#### 3.1 Create:
`python3 -m venv venv`
#### 3.2 Activate:
`source venv/bin/activate`
### 4. Install requirements
`pip install -r requirements.txt`
### 5. Move into data directory
`cd data`
### 6. Create database file and table structure
#### 6.1 Create:
`touch henhouse.db`
#### 6.2 Get into database file:
`sqlite3 henhouse.db`
#### 6.3 Paste code below to create table:
```
CREATE TABLE events (
    id INTEGER,
    chip_id INTEGER NOT NULL,
    event_time TIMESTAMP,
    reader_id TEXT NOT NULL,
    event_type INTEGER NOT NULL,
    in_api INTEGER NOT NULL DEFAULT 0,
    api_attempts INTEGER DEFAULT 1
);
```
#### 6.4 Exit from sqlite: `^D`
### 7. [OPTIONAL] Get api credentials, if you don't have them already
#### 7.1 Move back to root folder `/henhouse`:
`cd ..`
#### 7.2 Activate venv:
`python3 -m app.cli activate`
#### There you will enter the HWID and activation code and get login credentials for api
#### rows: `Username` and `Password`
### 8. Create configuration file
#### 8.1 Move back to `henhouse/data`:
`cd data`
#### 8.2 Create configuration file:
`nano config.ini`
#### Example configuration:
```
[API]
username = <Terminal username for api>
password = <Terminal password for api>
timezone_offset = 120
url = https://itaserver-staging.mobatime.cloud

[Constants]
lay_counter = 35
lay_time = 60
leave_time = 10

[DB]
file_path = ./data/henhouse.db
```
|      **Value**      | Description                                                                                                                                    |
|:-------------------:|------------------------------------------------------------------------------------------------------------------------------------------------|
| **timezone_offset** | Difference between UTC and Local time of the terminal in minutes. E.g local time in CEST is 120.                                               |
|       **url**       | Url of api server.                                                                                                                             |
|   **lay_counter**   | Number of chip reads to determine whether egg was laid. Recommend number slightly over half of lay time. (Chip is read ± 1.5 times per second) |
|    **lay_time**     | Duration of time(in seconds) to determine whether egg was laid.                                                                                |
|   **leave_time**    | Duration of time(in seconds) to determine whether chicken has left the reader.                                                                 |
|    **file_path**    | Path to database file <./path/from/root/dir.db>. Default:                                                                                      |
#### Save and exit: `^S ^X`

### 9. Run program
#### Return to root dir `/henhouse`:
`cd ..`
#### Start the app:
`python3 -m app`
#### or
`python3 -m app.cli run`

## Using CLI
### Can be used to run the app, get number of unsent records to api, ...
#### Use: `python3 -m app.cli --help` in `/henhouse` directory


