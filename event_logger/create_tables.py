import sqlite3
import yaml

# Load the app_conf.yaml configuration 
with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

conn = sqlite3.connect(app_config['datastore']['filename'])

c = conn.cursor()
c.execute('''
          CREATE TABLE Statistics
          (`id` INTEGER PRIMARY KEY ASC, 
           `message` TEXT NOT NULL,
           `code` TEXT NOT NULL,
           `date_created` VARCHAR(100) NOT NULL)
          ''')

conn.commit()
conn.close()