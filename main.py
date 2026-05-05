from fastapi import FastAPI
from zk_service import router as zk_router
from dotenv import load_dotenv
import os

load_dotenv()
app = FastAPI()
app.include_router(zk_router)