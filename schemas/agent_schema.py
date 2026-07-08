from pydantic import BaseModel
from datetime import datetime

from database.database import Base

class AgentSchema(BaseModel):
    id: str
    name: str
    system_prompt: str
    tools: list[str]
    model: str
    max_steps: int
    version: int
    created_at: datetime

class AgentCreateSchema(BaseModel):
    name: str
    system_prompt: str
    tools: list[str]
    model: str
    max_steps: int = 10

class AgentUpdateSchema(BaseModel):
    name: str
    system_prompt: str
    tools: list[str]
    model: str