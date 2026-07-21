from fastapi import APIRouter, HTTPException, status
from typing import List
from app.schemas.user_schema import UserResponseSchema, UserUpdateSchema
from app.services.user_service import user_service

router = APIRouter(prefix="/users", tags=["Users"])

# READ (Get All)
@router.get("/", response_model=List[UserResponseSchema])
def get_users():
    return user_service.get_all_users()

# READ (Get by ID)
@router.get("/{user_id}", response_model=UserResponseSchema)
def get_user(user_id: int):
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

# UPDATE (PUT)
@router.put("/{user_id}", response_model=UserResponseSchema)
def update_user(user_id: int, update_data: UserUpdateSchema):
    updated_user = user_service.update_user(user_id, update_data)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated_user

# DELETE
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int):
    success = user_service.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return None