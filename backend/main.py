import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

import backend.db as db

_STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    scheduler = BackgroundScheduler()
    scheduler.add_job(db.delete_old_readings, "interval", hours=1)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)


@app.get("/")
def dashboard():
    return FileResponse(_STATIC / "index.html")


@app.get("/readings")
def get_readings(
    last: Optional[int] = Query(default=None),
    from_ts: Optional[int] = Query(default=None, alias="from"),
    to_ts: Optional[int] = Query(default=None, alias="to"),
    bucket: Optional[int] = Query(default=None),
):
    using_last  = last is not None
    using_range = from_ts is not None or to_ts is not None

    if using_last and using_range:
        raise HTTPException(status_code=400, detail="Use 'last' or 'from'/'to', not both.")
    if using_last and last > 1000:
        raise HTTPException(status_code=400, detail="'last' must be 1000 or fewer.")

    if using_range:
        _from = from_ts or 0
        _to   = to_ts or int(time.time() * 1000)
        if bucket and bucket > 0:
            readings = db.get_readings_bucketed(_from, _to, bucket)
        else:
            readings = db.get_readings_range(_from, _to)
    else:
        readings = db.get_readings_last(last if using_last else 60)

    return {"count": len(readings), "readings": readings}
