from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import playbook_router

from app.routers import auth_router, user_router

app = FastAPI(
    title="User Management API",
    version="1.0.0",
    description="Backend endpoints for Signup, Login, and CRUD user operations."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],
)


app.include_router(auth_router.router)
app.include_router(user_router.router)
app.include_router(playbook_router.router)

@app.get("/")
def root():
    return {
        "message": "Welcome to the User Management API",
        "docs_url": "http://127.0.0.1:8000/docs"
    }