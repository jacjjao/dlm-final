from pydantic import BaseModel


class GenerateRequest(BaseModel):
    transcript: str


class GenerateResponse(BaseModel):
    type: str   # "code" | "chat"
    code: str   # non-empty when type == "code"
    reply: str  # non-empty when type == "chat"


class ExecuteRequest(BaseModel):
    code: str


class ExecuteResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int


class DebugRequest(BaseModel):
    code: str
    error: str
    transcript: str


class DebugResponse(BaseModel):
    code: str
    explanation: str
