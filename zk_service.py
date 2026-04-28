from fastapi import APIRouter, Query
from zk import ZK
from datetime import datetime
import calendar
from zoneinfo import ZoneInfo

router = APIRouter()

def parse_periode(periode: str):
    year, month = map(int, periode.split("-"))

    start = datetime(year, month, 1, 0, 0, 0)
    last_day = calendar.monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59)

    return start, end


def get_attendance(ip: str, port: int, periode: str = None):
    try:
        START_DATE = None
        END_DATE = None

        if periode:
            START_DATE, END_DATE = parse_periode(periode)
            print("FILTER PERIODE:", START_DATE, "s/d", END_DATE)

        zk = ZK(ip, port=port, timeout=20, password=0)
        conn = zk.connect()

        attendances = conn.get_attendance()
        result = []
        LIMIT = 10000
        count = 0
        
        print("TOTAL RAW FROM DEVICE:", len(attendances))
        print("PERIODE PARAM:", periode)
        print("START:", START_DATE, "END:", END_DATE)
        for att in attendances:
            try:
                ts = att.timestamp

                if ts.tzinfo is not None:
                    ts = ts.replace(tzinfo=None)

                if START_DATE and END_DATE:
                    if not (START_DATE <= ts <= END_DATE):
                        continue

                result.append({
                    "user_id": str(att.user_id),
                    "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": att.status
                })

                count += 1
                if count >= LIMIT:
                    break

            except Exception as e:
                print("ERROR PARSE ATT:", e)
                continue

        conn.disconnect()

        print("FILTERED RESULT:", len(result))

        return result

    except Exception as e:
        print("ERROR CONNECT ZK:", e)
        return []


@router.get("/attendance")
def attendance(
    ip: str,
    port: int = 4370,
    periode: str = Query(None)
):
    data = get_attendance(ip, port, periode)

    return {
        "success": True,
        "count": len(data),
        "data": data
    }


@router.get("/device-time")
def device_time(ip: str, port: int = 4370):
    try:
        zk = ZK(ip, port=port, timeout=5, password=0)
        conn = zk.connect()

        device_time_before = conn.get_time()

        now_wib = datetime.now(ZoneInfo("Asia/Jakarta")).replace(tzinfo=None)

        diff_seconds = abs((now_wib - device_time_before).total_seconds())

        synced = False

        if diff_seconds > 5:
            conn.set_time(now_wib)
            synced = True

        device_time_after = conn.get_time()

        now_after = datetime.now(ZoneInfo("Asia/Jakarta")).replace(tzinfo=None)
        diff_after = abs((now_after - device_time_after).total_seconds())

        conn.disconnect()

        return {
            "success": True,
            "before": device_time_before.strftime("%Y-%m-%d %H:%M:%S"),
            "after": device_time_after.strftime("%Y-%m-%d %H:%M:%S"),
            "server_time": now_after.strftime("%Y-%m-%d %H:%M:%S"),
            "difference_before": int(diff_seconds),
            "difference_after": int(diff_after),
            "synced": synced
        }

    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }