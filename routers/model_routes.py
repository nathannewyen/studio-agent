from fastapi import APIRouter

router = APIRouter(prefix="/v1/models")

# Maintained by hand — update when Anthropic ships new models.
SUPPORTED_MODELS = [
    {
        "id": "claude-haiku-4-5",
        "name": "Claude Haiku 4.5",
        "tier": "fast",
        "notes": "Cheapest, good for dev/testing",
    },
    {
        "id": "claude-sonnet-4-6",
        "name": "Claude Sonnet 4.6",
        "tier": "balanced",
        "notes": "Best quality/cost balance for demos",
    },
]


@router.get("/")
def list_models():
    return {"models": SUPPORTED_MODELS}