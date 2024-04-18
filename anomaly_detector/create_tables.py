import sqlite3
import yaml

# Load the app_conf.yaml configuration 
with open('app_conf.yaml', 'r') as f:
    app_config = yaml.safe_load(f.read())

conn = sqlite3.connect(app_config['datastore']['filename'])

c = conn.cursor()
c.execute('''
          CREATE TABLE anomaly_stats
          (id INTEGER PRIMARY KEY ASC, 
          device_id VARCHAR(250) NOT NULL,
          trace_id VARCHAR(250) NOT NULL,
          event_type VARCHAR(100) NOT NULL,
          anomaly_type VARCHAR(100) NOT NULL,
          description VARCHAR(250) NOT NULL,
          date_created VARCHAR(100) NOT NULL)
          ''')

conn.commit()
conn.close()
