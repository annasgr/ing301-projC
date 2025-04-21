import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from smarthouse.persistence import SmartHouseRepository
from pathlib import Path
import os
def setup_database():
    project_dir = Path(__file__).parent.parent
    db_file = project_dir / "data" / "db.sql" # you have to adjust this if you have changed the file name of the database
    return SmartHouseRepository(str(db_file.absolute()))

app = FastAPI()

repo = setup_database()

smarthouse = repo.load_smarthouse_deep()

if not (Path.cwd() / "www").exists():
    os.chdir(Path.cwd().parent)
if (Path.cwd() / "www").exists():
    # http://localhost:8000/welcome/index.html
    app.mount("/static", StaticFiles(directory="www"), name="static")


# http://localhost:8000/ -> welcome page
@app.get("/")
def root():
    return RedirectResponse("/static/index.html")


# Health Check / Hello World
@app.get("/hello")
def hello(name: str = "world"):
    return {"hello": name}


# Starting point ...

@app.get("/smarthouse")
def get_smarthouse_info() -> dict[str, int | float]:
    """
    This endpoint returns an object that provides information
    about the general structure of the smarthouse.
    """
    return {
        "no_rooms": len(smarthouse.get_rooms()),
        "no_floors": len(smarthouse.get_floors()),
        "registered_devices": len(smarthouse.get_devices()),
        "area": smarthouse.get_area()
    }

# TODO: implement the remaining HTTP endpoints as requested in
# https://github.com/selabhvl/ing301-projectpartC-startcode?tab=readme-ov-file#oppgavebeskrivelse
# here ...

@app.get("/smarthouse/floor")
def get_all_floors() -> list[int]:
    return [floor.level for floor in smarthouse.get_floors()]

@app.get("/smarthouse/floor/{fid}")
def get_rooms_on_floor(fid: int) -> list[str]:
    floor = next((f for f in smarthouse.get_floors() if f.level == fid), None)
    if floor is None:
        return []
    return [room.room_name if room.room_name else "Unnamed Room" for room in floor.rooms]

@app.get("/smarthouse/floor/{fid}/room")
def get_rooms_details(fid: int) -> list[dict]:
    floor = next((f for f in smarthouse.get_floors() if f.level == fid), None)
    if floor is None:
        return []
    return [
        {
            "name": room.room_name,
            "size": room.room_size,
            "devices": len(room.devices)
        }
        for room in floor.rooms
    ]
@app.get("/smarthouse/floor/{fid}/room/{rid}")
def get_single_room(fid: int, rid: int) -> dict:
    floor = next((f for f in smarthouse.get_floors() if f.level == fid), None)
    if floor is None or rid >= len(floor.rooms):
        return {}
    room = floor.rooms[rid]
    return {
        "name": room.room_name,
        "size": room.room_size,
        "devices": [d.id for d in room.devices]
    }

@app.get("/smarthouse/devices")
def get_all_devices() -> list[dict]:
    return [
        {
            "id": device.id,
            "model": device.model_name,
            "supplier": device.supplier,
            "type": device.device_type,
            "room": device.room.room_name if device.room else None
        }
        for device in smarthouse.get_devices()
    ]

@app.post("/smarthouse/device/{device_id}/state")
def set_actuator_state(device_id: str, new_state: float):
    device = smarthouse.get_device_by_id(device_id)
    if isinstance(device, Actuator):
        device.turn_on(new_state)
        repo.update_actuator_state(device)
        return {"status": "updated", "new_state": device.state}
    return {"error": "Device not found or not an actuator"}

@app.get("/smarthouse/device/{device_id}/measurement")
def get_latest_measurement(device_id: str):
    device = smarthouse.get_device_by_id(device_id)
    if isinstance(device, Sensor):
        measurement = repo.get_latest_reading(device)
        return vars(measurement) if measurement else {"message": "No data found"}
    return {"error": "Device not found or not a sensor"}

if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=8000)


