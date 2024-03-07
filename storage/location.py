from sqlalchemy import Column, Integer, String, DateTime, Double
from sqlalchemy.sql.functions import now
from base import Base
import datetime


class Location(Base):
    """ Location """

    __tablename__ = "location"

    id = Column(Integer, primary_key=True)
    device_id = Column(String(250), nullable=False)
    device_type = Column(String(250), nullable=False)
    timestamp = Column(String(100), nullable=False)
    date_created = Column(DateTime, nullable=False)
    gps_latitude = Column(Double, nullable=False)
    gps_longitude = Column(Double, nullable=False)
    trace_id = Column(String(250), nullable=False)

    def __init__(self, device_id, device_type, timestamp, gps_latitude, gps_longitude, trace_id):
        """ Initializes a location reading """
        self.device_id = device_id
        self.device_type = device_type
        self.timestamp = timestamp
        self.date_created = now() # Sets the date/time record is created
        self.gps_latitude = gps_latitude
        self.gps_longitude = gps_longitude
        self.trace_id = trace_id

    def to_dict(self):
        """ Dictionary Representation of a location reading """
        dict = {}
        dict['id'] = self.id
        dict['device_id'] = self.device_id
        dict['device_type'] = self.device_type
        dict['location_data'] = {}
        dict['location_data']['gps_latitude'] = self.gps_latitude
        dict['location_data']['gps_longitude'] = self.gps_longitude
        dict['timestamp'] = self.timestamp
        dict['date_created'] = self.date_created
        dict['trace_id'] = self.trace_id

        return dict
