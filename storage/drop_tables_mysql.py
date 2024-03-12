import mysql.connector

conn = mysql.connector.connect(host="ec2-52-40-150-21.us-west-2.compute.amazonaws.com", user="", 
password="", database="events")

c = conn.cursor()
c.execute('''
          DROP TABLE power_usage, location
          ''')

conn.commit()
conn.close()
