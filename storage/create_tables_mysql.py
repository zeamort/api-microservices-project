import mysql.connector

db_conn = mysql.connector.connect(
    host="ec2-52-40-150-21.us-west-2.compute.amazonaws.com", 
    user="", 
    password="", 
    database="events")

c = db_conn.cursor()
c.execute('''
          CREATE TABLE power_usage
          (`id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY, 
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
          (`id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY, 
           `device_id` VARCHAR(250) NOT NULL,
           `device_type` VARCHAR(250) NOT NULL,
           `gps_latitude` DOUBLE NOT NULL,
           `gps_longitude` DOUBLE NOT NULL,
           `timestamp` VARCHAR(100) NOT NULL,
           `date_created` VARCHAR(100) NOT NULL,
           `trace_id` VARCHAR(250) NOT NULL)
          ''')

db_conn.commit()
db_conn.close()
