import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.database import engine, Base
import routers.agent_routes, routers.run_routes, routers.trace_routes, routers.tool_routes, routers.model_routes

# Tells SQLAlchemy to automatically build your tables in Postgres if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI()

cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mounts all the endpoints from your agent_routes file onto the main app
app.include_router(routers.agent_routes.router)
app.include_router(routers.run_routes.router)
app.include_router(routers.trace_routes.router)
app.include_router(routers.tool_routes.router)
app.include_router(routers.model_routes.router)

@app.get("/")
def root():
    return {"status": "Application running successfully"}