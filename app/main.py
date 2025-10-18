from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.routers import leads, auth, admin
from app.database import init_database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Reddit Lead Finder MVP",
    description="Find businesses struggling on Reddit for lead generation",
    version="1.0.0"
)

# Add CORS middleware - this is the reliable way to handle preflight requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(leads.router, prefix="/api/leads", tags=["leads"])
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_database()
    logger.info("Database initialized successfully")

@app.get("/")
async def root():
    return {"message": "Reddit Lead Finder MVP API", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
