from sqlalchemy import Column, String, Integer, JSON, DateTime, Text
from database.database import Base
import datetime

class AgentModel(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    system_prompt = Column(Text, nullable=False)
    tools = Column(JSON, nullable=False)
    model = Column(String, nullable=False)
    max_steps = Column(Integer, default=10)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))