# Modelos de entrada/salida (Pydantic)

from pydantic import BaseModel

class TaskBase(BaseModel):
    title: str
    description: str | None = None
    completed : bool = False
    
class TaskCreate(TaskBase):
    pass 

class Task(TaskBase):
    id: int
    owner_id: int
    
    class Config:
        orm_mode = True
        
class UserBase(BaseModel):
    username: str
    
class UserCreate(UserBase):
    password: str
    
class User(UserBase):
    id: int
    
    class Config:
        orm_mode = True