import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.database import get_db
# Explicit schema and model imports
from schemas.agent_schema import AgentSchema, AgentCreateSchema, AgentUpdateSchema
from models.agent_model import AgentModel
from services import agent_service as AgentService

# Initialize the router instead of a FastAPI app instance
router = APIRouter(prefix="/v1/agents")

@router.get("/{id}", response_model = AgentSchema)
def get_agent(id: str, db: Session = Depends(get_db)):
    agent = AgentService.get_agent_by_id(id, db)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent

@router.post("/", response_model=AgentSchema, status_code=status.HTTP_201_CREATED)
def create_agent(agent_data: AgentCreateSchema, db: Session = Depends(get_db)):
    return AgentService.create_agent(agent_data, db)

@router.put("/{id}", response_model=AgentSchema)
def update_agent(id: str, agent_data: AgentUpdateSchema, db: Session = Depends(get_db)):
    agent = AgentService.update_agent(id, agent_data, db)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_agent(id: str, db: Session = Depends(get_db)):
    deleted = AgentService.remove_agent(id, db)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")