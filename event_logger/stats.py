from sqlalchemy import Column, Integer, String, DateTime, Numeric
from base import Base
import datetime


class Statistics(Base):
    """ Statistics """

    __tablename__ = "Statistics"

    id = Column(Integer, primary_key=True)
    message = Column(String, nullable=False)
    code = Column(String, nullable=False)
    date_created = Column(DateTime, nullable=False)

    def __init__(self, message, code, date_created):
        """ Initializes an event log """
        self.message = message
        self.code = code
        self.date_created = date_created

    def to_dict(self):
        """ Dictionary Representation of an event log """
        dict = {}
        dict['message'] = self.message
        dict['code'] = self.code
        dict['date_created'] = self.date_created

        return dict
