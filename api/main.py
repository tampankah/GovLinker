from fastapi import FastAPI
from api.routes import router

app = FastAPI(
    title="DMV Document Validator and Assistant",
    description="A combined API for document validation and DMV assistance.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://flutter-web-app-183025368636.us-central1.run.app"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the DMV Document Validator and Assistant API"}
