from fastapi import FastAPI
from api.routes import router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="DMV Document Validator and Assistant",
    description="A combined API for document validation and DMV assistance.",
    version="1.0.0",
)


# Allow all origins (you can specify the specific frontend URL for security)
origins = [
    "http://localhost:3000",  # Example for Flutter web; change as needed
    "http://localhost:46384",  # If you're running a different port for Flutter
]

# Add CORSMiddleware to allow CORS for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List the domains you want to allow
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods like GET, POST, OPTIONS
    allow_headers=["*"],  # Allow all headers
)

app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the DMV Document Validator and Assistant API"}
