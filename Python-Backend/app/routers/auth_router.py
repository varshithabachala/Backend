from fastapi import APIRouter, HTTPException, status
from app.schemas.user_schema import UserCreateSchema, UserLoginSchema, UserResponseSchema
from app.services.user_service import user_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=UserResponseSchema, status_code=status.HTTP_201_CREATED)
def signup(user_data: UserCreateSchema):
    try:
        new_user = user_service.create_user(user_data)
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login")
def login(credentials: UserLoginSchema):
    user = user_service.authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid username or password"
        )
    return {"message": "Login successful", "user_id": user["id"], "username": user["username"]}

@router.get("/dashboard")
def get_dashboard_data(username: str = None):
    """
    Dashboard endpoint reached after successful login.
    """
    if not username:
        return {
            "status": "success",
            "message": "Welcome to your Dashboard!",
            "data": {
                "user": "Guest User",
                "stats": {
                    "total_views": 120,
                    "active_sessions": 1,
                    "notifications": 3
                }
            }
        }  
    
    return {
        "status": "success",
        "message": f"Welcome back to your dashboard, {username}!",
        "data": {
            "user": username,
            "stats": {
                "total_views": 450,
                "active_sessions": 2,
                "notifications": 5
            },
            "recent_activity": [
                "Logged in recently",
                "Updated profile info"
            ]
        }
    }  