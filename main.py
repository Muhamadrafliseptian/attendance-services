from fastapi import FastAPI
from zk_service import router as zk_router

app = FastAPI()

app.include_router(zk_router)