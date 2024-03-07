from sqlalchemy import Column, Integer, String, DateTime, Numeric
from sqlalchemy.sql.functions import now
from base import Base
import datetime


class PowerUsage(Base):
    """ Power Usage """

    __tablename__ = "power_usage"

    id = Column(Integer, primary_key=True)
    device_id = Column(String(250), nullable=False)
    device_type = Column(String(250), nullable=False)
    timestamp = Column(String(100), nullable=False)
    date_created = Column(DateTime, nullable=False)
    energy_out_Wh = Column(Numeric, nullable=False)
    power_W = Column(Numeric, nullable=False)
    state_of_charge = Column(Integer, nullable=False)
    temperature_C = Column(Numeric, nullable=False)
    trace_id = Column(String(250), nullable=False)

    def __init__(self, device_id, device_type, timestamp, energy_out_Wh, power_W, state_of_charge, temperature_C, trace_id):
        """ Initializes a power usage reading """
        self.device_id = device_id
        self.device_type = device_type
        self.timestamp = timestamp
        self.date_created = now() # Sets the date/time record is created
        self.energy_out_Wh = energy_out_Wh
        self.power_W = power_W
        self.state_of_charge = state_of_charge
        self.temperature_C = temperature_C
        self.trace_id = trace_id

    def to_dict(self):
        """ Dictionary Representation of a power usage reading """
        dict = {}
        dict['id'] = self.id
        dict['device_id'] = self.device_id
        dict['device_type'] = self.device_type
        dict['power_data'] = {}
        dict['power_data']['energy_out_Wh'] = self.energy_out_Wh
        dict['power_data']['power_W'] = self.power_W
        dict['power_data']['state_of_charge_%'] = self.state_of_charge
        dict['power_data']['temperature_C'] = self.temperature_C
        dict['timestamp'] = self.timestamp
        dict['date_created'] = self.date_created
        dict['trace_id'] = self.trace_id

        return dict
