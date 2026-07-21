from typing import Dict, List, Optional
from app.schemas.user_schema import UserCreateSchema, UserUpdateSchema

class UserService:
    def __init__(self):
        # In-memory mock database: { id: user_dict }
        self._db: Dict[int, dict] = {}
        self._counter = 1

    def create_user(self, user_data: UserCreateSchema) -> dict:
        # Check for existing username
        for u in self._db.values():
            if u["username"] == user_data.username:
                raise ValueError("Username already exists.")

        user_dict = {
            "id": self._counter,
            "username": user_data.username,
            "email": user_data.email,
            "password": user_data.password  # In production, hash this password!
        }
        self._db[self._counter] = user_dict
        self._counter += 1
        return user_dict

    def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        for u in self._db.values():
            if u["username"] == username and u["password"] == password:
                return u
        return None

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        return self._db.get(user_id)

    def get_all_users(self) -> List[dict]:
        return list(self._db.values())

    def update_user(self, user_id: int, update_data: UserUpdateSchema) -> Optional[dict]:
        user = self._db.get(user_id)
        if not user:
            return None
        
        if update_data.email:
            user["email"] = update_data.email
        if update_data.password:
            user["password"] = update_data.password
            
        return user

    def delete_user(self, user_id: int) -> bool:
        if user_id in self._db:
            del self._db[user_id]
            return True
        return False

# Global singleton service instance
user_service = UserService()