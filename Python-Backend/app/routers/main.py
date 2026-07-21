from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth_router, user_router

app = FastAPI(
    title="User Management API",
    version="1.0.0",
    description="Backend endpoints for signup, login, and user CRUD operations."
)

# Enable CORS so your future HTML/JS frontend can interact with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth_router.router)
app.include_router(user_router.router)

@app.get("/")
def root():
    return {"message": "API is running. Visit /docs for Swagger documentation."}