from fastapi import FastAPI
from database.database import engine, Base
import routers.agent_routes

# Tells SQLAlchemy to automatically build your tables in Postgres if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Mounts all the endpoints from your agent_routes file onto the main app
app.include_router(routers.agent_routes.router  )

@app.get("/")
def root():
    return {"status": "Application running successfully"}