from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel

from my_agent.backend.adk_runner import ask_agent

app = FastAPI()


class ChatRequest(BaseModel):
    user_id: str
    message: str


@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        response = await ask_agent(
            req.user_id,
            req.message,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "response": response
    }
