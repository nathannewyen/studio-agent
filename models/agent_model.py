from sqlalchemy import Column, String, Integer, JSON, DateTime
from database.database import Base
import datetime

class AgentModel(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key = True)
    name = Column(String, nullable=False)
    definition = Column(String, nullable=False)
    version = Column(Integer, default = 1)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC))