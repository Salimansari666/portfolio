from typing import Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    max_new_tokens: Optional[int] = 200


class DatasetRequest(BaseModel):
    name: str
    subset: Optional[str] = None
    streaming: Optional[bool] = False


class VQARequest(BaseModel):
    question: str
    model: Optional[str] = None


class AnyToAnyRequest(BaseModel):
    input_type: str
    output_type: str
    model: Optional[str] = None
    question: Optional[str] = None
    text: Optional[str] = None
