from sqlalchemy import Column, ForeignKey, String, DateTime, Text
from database.database import Base
import datetime

class TracesModel(Base):
    __tablename__ = "traces"

    id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.id"))          # which agent handled it
    input = Column(Text)                                        # the user's original request
    status = Column(String, default="running")
    started_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))
    finished_at = Column(DateTime, nullable=True)