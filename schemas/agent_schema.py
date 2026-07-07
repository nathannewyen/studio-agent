from pydantic import BaseModel
from datetime import datetime

from database.database import Base

class AgentSchema(BaseModel):
    id: str
    name: str
    definition: str
    version: int
    created_at: datetime

class AgentCreateSchema(BaseModel):
    name: str
    definition: str

class AgentUpdateSchema(BaseModel):
    name: str
    definition: str