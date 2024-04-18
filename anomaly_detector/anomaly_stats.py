from sqlalchemy import Column, Integer, String, DateTime
from base import Base
import datetime


class AnomalyStats(Base):
    """ Anomaly """

    __tablename__ = "anomaly_stats"

    id = Column(Integer, primary_key=True)
    device_id = Column(String(250), nullable=False)
    trace_id = Column(String(250), nullable=False)
    event_type = Column(String(100), nullable=False)
    anomaly_type = Column(String(100), nullable=False)
    description = Column(String(250), nullable=False)
    date_created = Column(DateTime, nullable=False)

    def __init__(self, device_id, trace_id, event_type, anomaly_type, description):
        """ Initializes an anomaly """
        self.device_id = device_id
        self.trace_id = trace_id
        self.event_type = event_type
        self.anomaly_type = anomaly_type
        self.description = description
        self.date_created = datetime.datetime.now()  # Sets the date/time record is created

    def to_dict(self):
        """ Dictionary Representation of an anomaly """
        dict = {}
        dict['id'] = self.id
        dict['device_id'] = self.device_id
        dict['trace_id'] = self.trace_id
        dict['event_type'] = self.event_type
        dict['anomaly_type'] = self.anomaly_type
        dict['description'] = self.description

        return dict
