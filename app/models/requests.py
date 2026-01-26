from pydantic import BaseModel
from app.models.sgen import SGenSubmitRequest

class CreateJobRequest(BaseModel):
    config: SGenSubmitRequest
