
import json
import subprocess
import os
import sys
import uvicorn
import logging
from typing import List, Dict, Optional

# Import the new launcher
from app.mcp.main import app as fastapi_app_mcp

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global singleton instance
_server_launcher_instance = None

class ServerLauncher:
    def __new__(cls, config_dir: str = "app/launch_configs"):
        global _server_launcher_instance
        if _server_launcher_instance is None:
            _server_launcher_instance = super(ServerLauncher, cls).__new__(cls)
            _server_launcher_instance._initialized = False
        return _server_launcher_instance

    def __init__(self, config_dir: str = "app/launch_configs"):
        # Prevent re-initialization of the singleton
        if self._initialized:
            return
        
        self.config_dir = config_dir
        self.processes = {}  # Initialize the dictionary
        try:
            self.start_all_servers()
        except Exception as e:
            logger.error(f"Error during server launcher initialization: {str(e)}")
        
        self._initialized = True

    def get_available_configs(self) -> Dict[str, List[Dict]]:
        configs = {"chat": [], "embedding": []} 
        if not os.path.exists(self.config_dir):
            logger.warning(f"Config directory does not exist: {self.config_dir}")
            return configs
        
        try:
            for filename in os.listdir(self.config_dir):
                if filename.endswith(".json"):
                    config_data = self._load_config(filename)
                    if config_data and "configs" in config_data:
                        if filename.startswith("chat"):
                            configs["chat"] = config_data["configs"]
                        elif filename.startswith("embedding"):
                            configs["embedding"] = config_data["configs"]
        except OSError as e:
            logger.error(f"Error reading config directory {self.config_dir}: {str(e)}")
        
        return configs

    def _load_config(self, config_name: str) -> Optional[Dict]:
        config_path = os.path.join(self.config_dir, config_name)
        if not os.path.exists(config_path):
            logger.warning(f"Config file not found at {config_path}")
            return None
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading config file {config_path}: {str(e)}")
            return None

    def _save_config(self, config_name: str, data: Dict) -> None:
        config_path = os.path.join(self.config_dir, config_name)
        try:
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=4)
            logger.info(f"Config saved to {config_path}")
        except IOError as e:
            logger.error(f"Error saving config file {config_path}: {str(e)}")

    def start_server(self, server_type: str, config_name: str) -> None:
        """Start an external server process based on the configuration."""
        config_data = self._load_config(config_name)
        if not config_data:
            logger.error(f"Could not load config {config_name}")
            return
        
        active_index = config_data.get("active_config", 0)
        configs = config_data.get("configs", [])
        
        if active_index >= len(configs):
            logger.error(f"Active config index {active_index} is out of range for {config_name}")
            return
            
        config = configs[active_index]
        
        try:
            # Build the command
            command = [config["command"]] + config["args"]
            
            # Start the subprocess
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False  # Use shell=False for security
            )
            
            # Store the process
            self.processes[server_type] = process
            logger.info(f"Started {server_type} server with PID {process.pid}")
            
        except Exception as e:
            logger.error(f"Error starting {server_type} server: {str(e)}")

    def stop_server(self, server_type: str) -> None:
        """Stop an external server process."""
        if server_type not in self.processes:
            logger.warning(f"No running process found for {server_type}")
            return
            
        process = self.processes[server_type]
        
        if isinstance(process, subprocess.Popen):
            try:
                # Terminate the process gracefully
                process.terminate()
                try:
                    # Wait for the process to terminate with a timeout
                    process.wait(timeout=5)
                    logger.info(f"Process {server_type} terminated successfully")
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    process.kill()
                    logger.warning(f"Process {server_type} killed after timeout")
                    
                # Remove from processes dict
                del self.processes[server_type]
            except Exception as e:
                logger.error(f"Error stopping {server_type} server: {str(e)}")
        elif hasattr(process, 'is_alive') and hasattr(process, '_started'):
            # Handle thread-based processes (like the MCP server)
            logger.warning(f"Thread-based server {server_type} cannot be stopped directly")
            # Note: Thread termination is generally unsafe, so we just log a warning
        else:
            logger.warning(f"Unknown process type for {server_type}")
            if server_type in self.processes:
                del self.processes[server_type]

    def update_config(self, server_type: str, config_name: str, config_index: int) -> None:
        config_data = self._load_config(config_name)
        if config_data:
            config_data["active_config"] = config_index
            self._save_config(config_name, config_data)
            
            # Only restart if there's an active server process for this type and it's running
            if server_type in self.processes:
                is_running = False
                process_or_thread = self.processes[server_type]
                
                if isinstance(process_or_thread, subprocess.Popen):
                    is_running = process_or_thread.poll() is None
                elif hasattr(process_or_thread, 'is_alive'):
                    is_running = process_or_thread.is_alive()
                
                if is_running:
                    self.stop_server(server_type)
                    self.start_server(server_type, config_name)

    def start_all_servers(self) -> None:
        """Initialize the server launcher by starting the MCP server."""
        try:
            mcp_port = int(os.getenv("MCP_PORT", "8000"))  # Convert port to integer
            config = uvicorn.Config(fastapi_app_mcp, host="0.0.0.0", port=mcp_port, log_level="info")
            server = uvicorn.Server(config)

            # Run the server in a separate thread to avoid blocking the main thread
            import threading
            def run_server():
                server.run()

            thread = threading.Thread(target=run_server, daemon=True)  # daemon=True allows the main thread to exit without waiting
            thread.start()
            self.processes["mcp"] = thread # Store the thread for the MCP server
            logger.info(f"MCP server started on port {mcp_port}")
        except Exception as e:
            logger.error(f"Error starting MCP server: {str(e)}")   
        
    def stop_all_servers(self) -> None:
        """Stop all running server processes."""
        server_types = list(self.processes.keys())  # Create a list to avoid modification during iteration
        for server_type in server_types:
            self.stop_server(server_type)

    def get_server_status(self) -> Dict[str, bool]:
        status = {}
        for server_type, process_or_thread in self.processes.items():
            if isinstance(process_or_thread, subprocess.Popen):
                # For subprocess.Popen objects, use poll()
                status[server_type] = process_or_thread.poll() is None
            elif hasattr(process_or_thread, 'is_alive'):
                # For threading.Thread objects, use is_alive()
                status[server_type] = process_or_thread.is_alive()
            else:
                # For unknown types, assume not running
                status[server_type] = False
        return status

    def get_active_configs(self) -> Dict[str, int]:
        active_configs = {}
        chat_config = self._load_config("chat_server.json")
        if chat_config:
            active_configs["chat"] = chat_config.get("active_config", 0)
        else:
            logger.warning("Could not load chat server config")
        
        embedding_config = self._load_config("embedding_server.json")
        if embedding_config:
            active_configs["embedding"] = embedding_config.get("active_config", 0)
        else:
            logger.warning("Could not load embedding server config")
            
        return active_configs