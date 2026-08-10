from pydantic import BaseModel, EmailStr
from typing import Optional


class UserCreateSchema(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLoginSchema(BaseModel):
    username: str
    password: str

class UserUpdateSchema(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class UserResponseSchema(BaseModel):
    id: int
    username: str
    email: EmailStr

    class Config:
        from_attributes = True