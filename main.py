from fastapi import FastAPI
from zk_service import router as zk_router

app = FastAPI()

app.include_router(zk_router)

@app.get("/attendance")
def attendance(ip: str, port: int = 4370, periode: str = None):

    data = get_attendance(ip, port, periode)

    return {
        "success": True,
        "count": len(data or []),
        "data": data or []
    }