# app/config.py
from pydantic import BaseModel

class CsrfSettings(BaseModel):
    secret_key: str = "holahola7"
