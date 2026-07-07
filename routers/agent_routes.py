import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.database import get_db
# Explicit schema and model imports
from schemas.agent_schema import AgentSchema, AgentCreateSchema, AgentUpdateSchema
from models.agent_model import AgentModel

# Initialize the router instead of a FastAPI app instance
router = APIRouter(prefix="/v1/agents")

@router.get("/{id}", response_model = AgentSchema)
def get_agent(id: str, db: Session = Depends(get_db)):
    agent = db.query(AgentModel).filter(AgentModel.id == id).first()

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No agent available. Please create one!"
        )
    return agent

@router.post("/", response_model = AgentSchema, status_code=status.HTTP_201_CREATED)
def create_agent(agent_data: AgentCreateSchema, db: Session = Depends(get_db)):
    db_agent = AgentModel(
        id=str(uuid.uuid4()),
        name=agent_data.name,
        definition=agent_data.definition,
    )                                   
    db.add(db_agent)                    
    db.commit()                         
    db.refresh(db_agent)                
    return db_agent                     

@router.put("/{id}", response_model=AgentSchema)
def update_agent(id: str, agent_data: AgentUpdateSchema, db: Session = Depends(get_db)):
    agent = db.query(AgentModel).filter(AgentModel.id == id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.name = agent_data.name
    agent.definition = agent_data.definition
    
    db.commit()
    db.refresh(agent)
    return agent

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_agent(id: str, db: Session = Depends(get_db)):
    agent = db.query(AgentModel).filter(AgentModel.id == id).first()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    db.delete(agent)
    db.commit()
