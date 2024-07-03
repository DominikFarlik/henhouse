# Henhouse

### Clone git repository
`git clone git@github.com:DominikFarlik/henhouse.git`
### Move into project directory
`cd henhouse`
### Create and activate virtual env
#### Create:
`python3 -m venv venv`
#### Activate:
`source venv/bin/activate`
### Install requirements
`pip install -r requirements.txt`
### [OPTIONAL] Get api credentials, if you don't have them already
`python3 -m app.cli activate`
#### There you will enter the HWID and activation code and get login credentials for api
#### rows: `Username` and `Password`
### Create configuration file
#### Create configuration file:
`nano data/config.ini`
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

### Run program
`python3 -m app`
#### or
`python3 -m app.cli run`

## Using CLI
### Can be used to run the app, get number of unsent records to api, ...
#### Use: `python3 -m app.cli --help`


