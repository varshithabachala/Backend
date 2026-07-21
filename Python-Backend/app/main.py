from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers from the routers package inside app
from app.routers import auth_router, user_router

# Initialize FastAPI app
app = FastAPI(
    title="User Management API",
    version="1.0.0",
    description="Backend endpoints for Signup, Login, and CRUD user operations."
)

# Enable CORS (Cross-Origin Resource Sharing)
# This allows your future HTML/JavaScript frontend to communicate with this backend API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (adjust for production)
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],
)

# Include the API Routers
app.include_router(auth_router.router)
app.include_router(user_router.router)

# Root Endpoint
@app.get("/")
def root():
    return {
        "message": "Welcome to the User Management API",
        "docs_url": "http://127.0.0.1:8000/docs"
    }