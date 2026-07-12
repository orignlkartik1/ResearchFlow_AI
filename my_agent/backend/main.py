from fastapi import FastAPI
from pydantic import BaseModel

from my_agent.backend.adk_runner import ask_agent

app = FastAPI()


class ChatRequest(BaseModel):
    user_id: str
    message: str


@app.post("/chat")
async def chat(req: ChatRequest):
    response = await ask_agent(
        req.user_id,
        req.message,
    )

    return {
        "response": response
    }