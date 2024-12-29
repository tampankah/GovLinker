from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router

app = FastAPI(
    title="DMV Document Validator and Assistant",
    description="A combined API for document validation and DMV assistance.",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://flutter-web-app-183025368636.us-central1.run.app", 
        "https://government-assistant-api-183025368636.us-central1.run.app"  
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the DMV Document Validator and Assistant API"}