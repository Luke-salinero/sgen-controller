from typing import Dict, Any
from pydantic import BaseModel

class CreateJobRequest(BaseModel):
    config: Dict[str, Any]
    api_key_owner: str