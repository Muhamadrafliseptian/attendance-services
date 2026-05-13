from fastapi import APIRouter, Query
from zk import ZK
from datetime import datetime
import calendar
import os
from zoneinfo import ZoneInfo
from fastapi import Body
import traceback
from fastapi import Depends, Header, HTTPException
from config import API_KEY

def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

router = APIRouter(dependencies=[Depends(verify_api_key)])

def parse_periode(periode: str):
    year, month = map(int, periode.split("-"))

    start = datetime(year, month, 1, 0, 0, 0)
    last_day = calendar.monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59)

    return start, end


def get_attendance(ip: str, port: int, periode: str = None, last_pull: str = None):
    START_DATE = None
    END_DATE = None
    last_pull_dt = None

    if last_pull:
        try:
            last_pull_dt = datetime.strptime(last_pull, "%Y-%m-%d %H:%M:%S")
        except Exception:
            last_pull_dt = None
    
    if periode:
        START_DATE, END_DATE = parse_periode(periode)

    zk = ZK(ip, port=port, timeout=20, password=0)
    conn = zk.connect()

    try:
        attendances = conn.get_attendance()
        result = []

        # LIMIT = 10000
        count = 0

        for att in attendances:
            ts = att.timestamp

            if ts.tzinfo is not None:
                ts = ts.replace(tzinfo=None)
            
            if last_pull_dt and ts <= last_pull_dt:
                continue

            if START_DATE and END_DATE:
                if not (START_DATE <= ts <= END_DATE):
                    continue

            result.append({
                "user_id": str(att.user_id),
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "status": att.status
            })

            # count += 1
            # if count >= LIMIT:
            #     break

        return result

    finally:
        conn.disconnect()
        
def get_users(ip: str, port: int):
    zk = ZK(ip, port=port, timeout=20, password=0)
    conn = zk.connect()

    try:
        users = conn.get_users()
        result = []

        for user in users:
            result.append({
                "uid": user.uid,
                "user_id": str(user.user_id),
                "name": user.name,
                "role": user.privilege,
            })

        return result

    finally:
        conn.disconnect()

@router.post("/attendance")
def attendance(payload: dict = Body(...)):
    try:
        ip = payload.get("ip")
        port = int(payload.get("port", 4370))
        periode = payload.get("periode")
        last_pull = payload.get("last_pull")
        
        if not ip:
            raise HTTPException(status_code=400, detail="IP is required")

        data = get_attendance(ip, port, periode, last_pull)

        return {
            "success": True,
            "count": len(data),
            "data": data
        }

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users")
def users(payload: dict = Body(...)):
    try:
        ip = payload.get("ip")
        port = int(payload.get("port", 4370))

        if not ip:
            raise HTTPException(status_code=400, detail="IP is required")

        data = get_users(ip, port)

        return {
            "success": True,
            "count": len(data),
            "data": data
        }

    except HTTPException as e:
        raise e

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        def safe_call(fn):
                try:
                    return fn()
                except:
                    return None
        device_info = {
            "device_name": safe_call(conn.get_device_name),
            "serial_number": safe_call(conn.get_serialnumber),
            "firmware_version": safe_call(conn.get_firmware_version),
            "platform": safe_call(conn.get_platform),
            "mac_address": safe_call(conn.get_mac),

            "device_time": safe_call(conn.get_time),

            "fingerprint_version": safe_call(conn.get_fp_version),
            "face_version": safe_call(conn.get_face_version),

            "pin_width": safe_call(conn.get_pin_width),
        }

        conn.disconnect()

        return {
            "success": True,
            "before": device_time_before.strftime("%Y-%m-%d %H:%M:%S"),
            "after": device_time_after.strftime("%Y-%m-%d %H:%M:%S"),
            "server_time": now_after.strftime("%Y-%m-%d %H:%M:%S"),
            "difference_before": int(diff_seconds),
            "difference_after": int(diff_after),
            "data": device_info,
            "synced": synced
        }

    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }

@router.post("/check-connection")
def check_connection(payload: dict = Body(...)):
    try:
        ip = payload.get("ip")
        port = int(payload.get("port", 4370))

        if not ip:
            raise HTTPException(status_code=400, detail="IP is required")

        zk = ZK(ip,
    port=port,
    timeout=60,
    password=0,
    force_udp=False,
    ommit_ping=True)

        try:
            conn = zk.connect()
            def safe_call(fn):
                try:
                    return fn()
                except:
                    return None

            device_info = {
            "device_name": safe_call(conn.get_device_name),
            "serial_number": safe_call(conn.get_serialnumber),
            "firmware_version": safe_call(conn.get_firmware_version),
            "platform": safe_call(conn.get_platform),
            "mac_address": safe_call(conn.get_mac),

            "device_time": safe_call(conn.get_time),

            "fingerprint_version": safe_call(conn.get_fp_version),
            "face_version": safe_call(conn.get_face_version),

            "pin_width": safe_call(conn.get_pin_width),
        }

            conn.disconnect()

            return {
                "success": True,
                "message": "Device connected successfully",
                "data": device_info
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to connect: {str(e)}"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/check-multiple")
def check_multiple(payload: dict = Body(...)):
    devices = payload.get("devices", [])

    results = []

    for dev in devices:
        ip = dev.get("ip")
        port = int(dev.get("port", 4370))

        zk = ZK(ip, port=port, timeout=3, password=0)

        try:
            conn = zk.connect()
            conn.disconnect()

            results.append({
                "ip": ip,
                "status": "online",
            })
        except:
            results.append({
                "ip": ip,
                "status": "offline"
            })

    return {
        "success": True,
        "data": results
    }
    
@router.post("/delete-user")
def delete_user(payload: dict = Body(...)):
    try:
        ip = payload.get("ip")
        port = int(payload.get("port", 4370))
        uid = payload.get("uid")

        if not ip or uid is None:
            raise HTTPException(status_code=400, detail="IP dan uid wajib")

        zk = ZK(ip, port=port, timeout=10, password=0)
        conn = zk.connect()

        try:
            conn.delete_user(uid=int(uid))

            return {
                "success": True,
                "message": "User berhasil dihapus"
            }

        finally:
            conn.disconnect()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/set-user")
def set_user(payload: dict = Body(...)):
    try:
        ip = payload.get("ip")
        port = int(payload.get("port", 4370))
        uid = payload.get("uid")
        user_id = payload.get("user_id")
        name = payload.get("name", "Unknown")

        if not ip or not user_id or uid is None:
            raise HTTPException(status_code=400, detail="IP, uid dan user_id wajib")

        zk = ZK(ip, port=port, timeout=10, password=0)
        conn = zk.connect()

        try:
            conn.set_user(
                uid=int(uid),
                name=str(name),
                privilege=0,
                password='',  
                group_id='0',
                user_id=str(user_id)
            )

            return {
                "success": True,
                "message": "User berhasil ditambahkan"
            }

        finally:
            conn.disconnect()

    except Exception as e:
        import traceback
        print("ERROR:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))