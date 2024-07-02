# Henouse

### 1. Clone git repository
#### git clone git@github.com:DominikFarlik/henhouse.git
### 2. Move into project directory
#### cd henhouse
### 3. Create and activate virtual env
#### python3 -m venv venv
#### source venv/bin/activate
### 4. Install requirements
#### pip install -r requirements
### 5. Move "data" directory
#### cd data
### 6. Create database file and table structure
#### touch henhouse.db
#### sqlite3 henhouse.db
#### __________________________
#### CREATE TABLE events (
####     id INTEGER,
####     chip_id INTEGER NOT NULL,
####     event_time TIMESTAMP,
####     reader_id TEXT NOT NULL,
####     event_type INTEGER NOT NULL,
####     in_api INTEGER NOT NULL DEFAULT 0,
####     api_attempts INTEGER DEFAULT 1
#### );
#### __________________________
### 7. Create configuration file 



