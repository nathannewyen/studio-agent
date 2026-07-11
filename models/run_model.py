from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Text
from database.database import Base
import datetime

class RunsModel(Base):
    __tablename__ = "runs"

    id = Column(String, primary_key=True)
    trace_id = Column(String, ForeignKey("traces.id"))
    model_name = Column(String)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)           # usage/cost for this run
    status = Column(String, default="running")
    started_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))
    finished_at = Column(DateTime, nullable=True)