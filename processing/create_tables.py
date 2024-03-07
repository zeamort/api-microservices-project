import sqlite3
import yaml

# Load the app_conf.yaml configuration 
with open('app_conf.yaml', 'r') as f:
    app_config = yaml.safe_load(f.read())

conn = sqlite3.connect(app_config['datastore']['filename'])

c = conn.cursor()
c.execute('''
          CREATE TABLE Statistics
          (`id` INTEGER PRIMARY KEY ASC, 
           `date_created` VARCHAR(100) NOT NULL,
           `total_power_usage_events` INTEGER NOT NULL,
           `max_power_W` FLOAT NOT NULL,
           `average_state_of_charge` FLOAT NOT NULL,
           `max_temperature_C` FLOAT NOT NULL,
           `total_location_events` INTEGER NOT NULL)
          ''')

conn.commit()
conn.close()
