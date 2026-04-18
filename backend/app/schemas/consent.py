from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ConsentTextOut(BaseModel):
    version: str
    text_hash: str
    body_markdown: str
    body_html: str


class ConsentAcceptIn(BaseModel):
    version: str
    text_hash: str  # client must echo what they actually saw


class ConsentOut(BaseModel):
    id: UUID
    user_id: UUID
    version: str
    text_hash: str
    signature_hash: str
    created_at: datetime
