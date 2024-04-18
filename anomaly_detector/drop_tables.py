import sqlite3

conn = sqlite3.connect('stats.sqlite')

c = conn.cursor()
c.execute('''
          DROP TABLE Anomaly
          ''')

conn.commit()
conn.close()
