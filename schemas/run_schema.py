from pydantic import BaseModel

class RunRequest(BaseModel):
    question: str
    agent_id: str