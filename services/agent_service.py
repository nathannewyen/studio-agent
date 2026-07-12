import uuid
from models.agent_model import AgentModel

def get_all_agents(db):
    return db.query(AgentModel).all()

def get_agent_by_id(agent_id, db):
    return db.query(AgentModel).filter(AgentModel.id == agent_id).first()

def create_agent(agent_data, db):
    db_agent = AgentModel(
        id=str(uuid.uuid4()),
        name=agent_data.name,
        system_prompt=agent_data.system_prompt,
        tools=agent_data.tools,
        model=agent_data.model,
        max_steps=agent_data.max_steps
    )

    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent

def update_agent(agent_id, agent_data, db):
    agent = get_agent_by_id(agent_id, db)

    if agent is None:
        return None
    
    agent.name = agent_data.name
    agent.system_prompt = agent_data.system_prompt
    agent.tools = agent_data.tools
    agent.model = agent_data.model

    db.commit()
    db.refresh(agent)
    return agent

def remove_agent(agent_id, db):
    agent = get_agent_by_id(agent_id, db)
    if agent is None:
        return False
    
    db.delete(agent)
    db.commit()
    return True