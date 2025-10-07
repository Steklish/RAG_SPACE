
import json
import subprocess
import os
from typing import List, Dict, Optional

class ServerLauncher:
    def __init__(self, config_dir: str = "app/launch_configs"):
        self.config_dir = config_dir
        self.processes: Dict[str, subprocess.Popen] = {}

    def get_available_configs(self) -> Dict[str, List[Dict]]:
        configs = {"chat": [], "embedding": []}
        if not os.path.exists(self.config_dir):
            return configs
        
        for filename in os.listdir(self.config_dir):
            if filename.endswith(".json"):
                config_data = self._load_config(filename)
                if config_data and "configs" in config_data:
                    if filename.startswith("chat"):
                        configs["chat"] = config_data["configs"]
                    elif filename.startswith("embedding"):
                        configs["embedding"] = config_data["configs"]
        return configs

    def _load_config(self, config_name: str) -> Optional[Dict]:
        config_path = os.path.join(self.config_dir, config_name)
        if not os.path.exists(config_path):
            print(f"Warning: Config file not found at {config_path}")
            return None
        with open(config_path, 'r') as f:
            return json.load(f)

    def _save_config(self, config_name: str, data: Dict) -> None:
        config_path = os.path.join(self.config_dir, config_name)
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=4)

    def start_server(self, server_type: str, config_name: str) -> None:
        if self.processes.get(server_type) and self.processes[server_type].poll() is None:
            print(f"Server {server_type} is already running.")
            return

        config_data = self._load_config(config_name)
        if config_data:
            active_config_index = config_data.get("active_config", 0)
            config = config_data["configs"][active_config_index]
            
            command = [config["command"]] + config["args"]
            print(f"Starting {server_type} server with command: {' '.join(command)}")
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.processes[server_type] = process
            print(f"Server {server_type} ({config_name}) started with PID: {process.pid}")

    def stop_server(self, server_type: str) -> None:
        if server_type in self.processes:
            self.processes[server_type].terminate()
            del self.processes[server_type]
            print(f"Server {server_type} stopped.")

    def update_config(self, server_type: str, config_name: str, config_index: int) -> None:
        config_data = self._load_config(config_name)
        if config_data:
            config_data["active_config"] = config_index
            self._save_config(config_name, config_data)
            
            if self.processes.get(server_type) and self.processes[server_type].poll() is None:
                self.stop_server(server_type)
                self.start_server(server_type, config_name)

    def start_all_servers(self) -> None:
        configs = self.get_available_configs()
        if configs["chat"]:
            self.start_server("chat", "chat_server.json")
        if configs["embedding"]:
            self.start_server("embedding", "embedding_server.json")

    def stop_all_servers(self) -> None:
        for server_type in list(self.processes.keys()):
            self.stop_server(server_type)
        print("All servers stopped.")

    def get_server_status(self) -> Dict[str, bool]:
        status = {}
        for server_type, process in self.processes.items():
            status[server_type] = process.poll() is None
        return status

    def get_active_configs(self) -> Dict[str, int]:
        active_configs = {}
        chat_config = self._load_config("chat_server.json")
        if chat_config:
            active_configs["chat"] = chat_config.get("active_config", 0)
        
        embedding_config = self._load_config("embedding_server.json")
        if embedding_config:
            active_configs["embedding"] = embedding_config.get("active_config", 0)
            
        return active_configs

if __name__ == "__main__":
    launcher = ServerLauncher()
    launcher.start_all_servers()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        launcher.stop_all_servers()
