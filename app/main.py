import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError
import time

from app.config import settings
from app.database import Base, engine
from app.routes import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Wait for DB to start up and create tables (lifespan event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Retry database connection in container environments
    retries = 5
    connected = False
    while retries > 0:
        try:
            logger.info("Initializing database and creating tables...")
            Base.metadata.create_all(bind=engine)
            connected = True
            break
        except OperationalError as e:
            logger.warning(f"Database connection failed: {e}. Retrying in 2 seconds...")
            retries -= 1
            time.sleep(2)
    if not connected:
        logger.error("Could not connect to the database. Exiting lifespan setup.")
        raise RuntimeError("Database connection failure")
    
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Asynchronous transactional pipeline with rule-based anomaly detection & LLM analysis",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include modular application routes
app.include_router(router)
