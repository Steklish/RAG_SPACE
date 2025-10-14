from fastapi import APIRouter, HTTPException
from app.server_launcher import ServerLauncher
from app.schemas import ServerStartRequest, ServerStopRequest, ServerUpdateConfig
from app.utils.helpers import safe_json

router = APIRouter()
server_launcher = ServerLauncher()

@router.get("/configs")
def get_server_configs():
    return safe_json(server_launcher.get_available_configs())

@router.post("/start")
def start_servers(req: ServerStartRequest):
    server_launcher.start_server(req.server_type, req.config_name)
    return safe_json({"status": "success", "message": f"{req.server_type} server started."})

@router.post("/stop")
def stop_servers(req: ServerStopRequest):
    server_launcher.stop_server(req.server_type)
    return safe_json({"status": "success", "message": f"{req.server_type} server stopped."})

@router.post("/update_config")
def update_server_config(req: ServerUpdateConfig):
    server_launcher.update_config(req.server_type, req.config_name, req.config_index)
    return safe_json({"status": "success", "message": f"{req.server_type} server config updated and restarted."})

@router.get("/status")
def get_server_status():
    return safe_json(server_launcher.get_server_status())

@router.get("/active_configs")
def get_active_configs():
    return safe_json(server_launcher.get_active_configs())