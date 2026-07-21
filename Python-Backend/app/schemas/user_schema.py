from pydantic import BaseModel, EmailStr
from typing import Optional

# Request schema for Signup
class UserCreateSchema(BaseModel):
    username: str
    email: EmailStr
    password: str

# Request schema for Login
class UserLoginSchema(BaseModel):
    username: str
    password: str

# Request schema for Updating User
class UserUpdateSchema(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None

# Response schema
class UserResponseSchema(BaseModel):
    id: int
    username: str
    email: EmailStr

    class Config:
        from_attributes = True