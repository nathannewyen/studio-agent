from sqlalchemy import JSON, Column, ForeignKey, Integer, String, Text
from database.database import Base

class RunStepsModel(Base):
    __tablename__ = "run_steps"

    id = Column(String, primary_key=True)
    run_id = Column(String, ForeignKey("runs.id"))
    step_index = Column(Integer)
    type = Column(String)
    name = Column(String, nullable=True)
    input_payload = Column(JSON)
    output_payload = Column(JSON)
    status = Column(String)
    latency_ms = Column(Integer)
    error = Column(Text, nullable=True)