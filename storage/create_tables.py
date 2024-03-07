import sqlite3

conn = sqlite3.connect('readings.sqlite')

c = conn.cursor()
c.execute('''
          CREATE TABLE power_usage
          (`id` INTEGER PRIMARY KEY ASC, 
           `device_id` VARCHAR(250) NOT NULL,
           `device_type` VARCHAR(250) NOT NULL,
           `power_W` FLOAT NOT NULL,
           `energy_out_Wh` FLOAT NOT NULL,
           `state_of_charge` INTEGER NOT NULL,
           `temperature_C` FLOAT NOT NULL,
           `timestamp` VARCHAR(100) NOT NULL,
           `date_created` VARCHAR(100) NOT NULL,
           `trace_id` VARCHAR(250) NOT NULL)
          ''')

c.execute('''
          CREATE TABLE location
          (`id` INTEGER PRIMARY KEY ASC, 
           `device_id` VARCHAR(250) NOT NULL,
           `device_type` VARCHAR(250) NOT NULL,
           `gps_latitude` DOUBLE NOT NULL,
           `gps_longitude` DOUBLE NOT NULL,
           `timestamp` VARCHAR(100) NOT NULL,
           `date_created` VARCHAR(100) NOT NULL,
           `trace_id` VARCHAR(250) NOT NULL)
          ''')

conn.commit()
conn.close()
