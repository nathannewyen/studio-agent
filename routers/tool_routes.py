from fastapi import APIRouter
from services.tools.langchain_tools import TOOL_CATALOG

router = APIRouter(prefix="/v1/tools")


@router.get("/")
def list_tools():
    return {"tools": TOOL_CATALOG}