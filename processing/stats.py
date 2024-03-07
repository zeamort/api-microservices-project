from sqlalchemy import Column, Integer, String, DateTime, Numeric
from sqlalchemy.sql.functions import now
from base import Base
import datetime


class Statistics(Base):
    """ Statistics """

    __tablename__ = "Statistics"

    id = Column(Integer, primary_key=True)
    date_created = Column(DateTime, nullable=False)
    total_power_usage_events = Column(Integer, nullable=False)
    max_power_W = Column(Numeric, nullable=False)
    average_state_of_charge = Column(Integer, nullable=False)
    max_temperature_C = Column(Numeric, nullable=False)
    total_location_events = Column(Integer, nullable=False)

    def __init__(self, date_created, total_power_usage_events, max_power_W, average_state_of_charge, max_temperature_C, total_location_events):
        """ Initializes a power usage reading """
        self.date_created = date_created
        self.total_power_usage_events = total_power_usage_events
        self.max_power_W = max_power_W
        self.average_state_of_charge = average_state_of_charge
        self.max_temperature_C = max_temperature_C
        self.total_location_events = total_location_events


    def to_dict(self):
        """ Dictionary Representation of a power usage reading """
        dict = {}
        dict['date_created'] = self.date_created
        dict['total_power_usage_events'] = self.total_power_usage_events
        dict['total_location_events'] = self.total_location_events
        dict['max_power_W'] = self.max_power_W
        dict['average_state_of_charge'] = self.average_state_of_charge
        dict['max_temperature_C'] = self.max_temperature_C

        return dict
