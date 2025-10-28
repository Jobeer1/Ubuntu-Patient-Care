"""Module management routes for starting/stopping services"""
import os
import subprocess
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import psutil
import requests

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/modules", tags=["modules"])

# Module configurations
MODULES_CONFIG = {
    "dictation": {
        "port": 5443,
        "name": "Dictation Service",
        "startup_script": None,  # Will be configured
        "process_name": "dictation",
        "url": "https://localhost:5443"
    },
    "pacs": {
        "port": 5000,
        "name": "PACS Service",
        "startup_script": None,
        "process_name": "pacs",
        "url": "http://localhost:5000"
    },
    "ris": {
        "port": 3001,
        "name": "RIS Backend",
        "startup_script": None,
        "process_name": "ris",
        "url": "http://localhost:3001"
    },
    "billing": {
        "port": 3000,
        "name": "Billing/Frontend",
        "startup_script": None,
        "process_name": "billing",
        "url": "http://localhost:3000"
    }
}

# Store running processes
running_processes: Dict[str, subprocess.Popen] = {}


class ModuleStatusResponse(BaseModel):
    """Response model for module status"""
    module: str
    running: bool
    port: int
    status: str
    message: str


class ModuleActionResponse(BaseModel):
    """Response model for module actions"""
    module: str
    action: str
    success: bool
    message: str


def is_port_open(port: int) -> bool:
    """Check if a port is open/accessible"""
    try:
        # First check if port is listening (most reliable)
        for conn in psutil.net_connections():
            if conn.laddr.port == port and conn.status == 'LISTEN':
                return True
        
        # If port is listening, it's open
        return False
    except Exception as e:
        logger.debug(f"Error checking port {port}: {str(e)}")
        return False


def is_process_running(module: str) -> bool:
    """Check if a module process is running"""
    config = MODULES_CONFIG.get(module)
    if not config:
        return False
    
    port = config["port"]
    return is_port_open(port)


@router.get("/status", response_model=Dict[str, ModuleStatusResponse])
async def get_all_modules_status():
    """Get status of all modules"""
    statuses = {}
    
    for module_id, config in MODULES_CONFIG.items():
        running = is_process_running(module_id)
        statuses[module_id] = ModuleStatusResponse(
            module=module_id,
            running=running,
            port=config["port"],
            status="running" if running else "stopped",
            message=f"{config['name']} is {'running' if running else 'stopped'}"
        )
    
    return statuses


@router.get("/status/{module_id}", response_model=ModuleStatusResponse)
async def get_module_status(module_id: str):
    """Get status of a specific module"""
    if module_id not in MODULES_CONFIG:
        raise HTTPException(status_code=404, detail=f"Module '{module_id}' not found")
    
    config = MODULES_CONFIG[module_id]
    running = is_process_running(module_id)
    
    return ModuleStatusResponse(
        module=module_id,
        running=running,
        port=config["port"],
        status="running" if running else "stopped",
        message=f"{config['name']} is {'running' if running else 'stopped'}"
    )


@router.post("/start/{module_id}", response_model=ModuleActionResponse)
async def start_module(module_id: str):
    """Start a module"""
    if module_id not in MODULES_CONFIG:
        raise HTTPException(status_code=404, detail=f"Module '{module_id}' not found")
    
    config = MODULES_CONFIG[module_id]
    
    # Check if already running
    if is_process_running(module_id):
        return ModuleActionResponse(
            module=module_id,
            action="start",
            success=True,
            message=f"{config['name']} is already running on port {config['port']}"
        )
    
    try:
        # Map modules to their startup logic
        if module_id == "dictation":
            # Start dictation service
            message = start_dictation_service()
        elif module_id == "pacs":
            # Start PACS service
            message = start_pacs_service()
        elif module_id == "ris":
            # Start RIS service
            message = start_ris_service()
        elif module_id == "billing":
            # Start Billing service
            message = start_billing_service()
        else:
            raise ValueError(f"Unknown module: {module_id}")
        
        logger.info(f"Started {module_id}: {message}")
        
        return ModuleActionResponse(
            module=module_id,
            action="start",
            success=True,
            message=message
        )
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to start {module_id}: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start {config['name']}: {error_msg}"
        )


@router.post("/stop/{module_id}", response_model=ModuleActionResponse)
async def stop_module(module_id: str):
    """Stop a module"""
    if module_id not in MODULES_CONFIG:
        raise HTTPException(status_code=404, detail=f"Module '{module_id}' not found")
    
    config = MODULES_CONFIG[module_id]
    
    # Check if already stopped
    if not is_process_running(module_id):
        return ModuleActionResponse(
            module=module_id,
            action="stop",
            success=True,
            message=f"{config['name']} is already stopped"
        )
    
    try:
        # Map modules to their shutdown logic
        if module_id == "dictation":
            # Stop dictation service
            message = stop_dictation_service()
        elif module_id == "pacs":
            # Stop PACS service
            message = stop_pacs_service()
        elif module_id == "ris":
            # Stop RIS service
            message = stop_ris_service()
        elif module_id == "billing":
            # Stop Billing service
            message = stop_billing_service()
        else:
            raise ValueError(f"Unknown module: {module_id}")
        
        logger.info(f"Stopped {module_id}: {message}")
        
        return ModuleActionResponse(
            module=module_id,
            action="stop",
            success=True,
            message=message
        )
    
    except Exception as e:
        logger.error(f"Failed to stop {module_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop {config['name']}: {str(e)}"
        )


# Module-specific startup/shutdown functions

def start_dictation_service() -> str:
    """Start the dictation service"""
    try:
        # Start the medical-reporting-module Flask app
        dictation_path = Path("C:/Users/Admin/Desktop/ELC/Ubuntu-Patient-Care/4-PACS-Module/Orthanc/medical-reporting-module")
        
        if not dictation_path.exists():
            raise FileNotFoundError(f"Dictation module not found at {dictation_path}")
        
        # Start the Flask app in a new process
        import platform
        import time
        
        if platform.system() == "Windows":
            # Use py command for proper Python execution on Windows
            cmd = f'cd /d "{dictation_path}" && py app.py'
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=None,  # Allow console output to be visible
                stderr=None,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            # Use python3 on Unix/Linux
            process = subprocess.Popen(
                ["python3", "app.py"],
                cwd=str(dictation_path),
                stdout=None,
                stderr=None,
                preexec_fn=os.setsid
            )
        
        # Give it a moment to start
        time.sleep(0.5)
        
        # Check if process is still alive
        poll = process.poll()
        if poll is not None:
            raise Exception(f"Process exited immediately with code {poll}. Check if Python is installed and in PATH.")
        
        # Store process reference
        running_processes["dictation"] = process
        logger.info(f"Dictation service started with PID: {process.pid}")
        return f"Dictation service started (PID: {process.pid}). Check the console window for Whisper model loading..."
    except Exception as e:
        logger.error(f"Dictation startup error: {str(e)}")
        raise Exception(f"Dictation startup failed: {str(e)}")


def stop_dictation_service() -> str:
    """Stop the dictation service"""
    try:
        # First try to terminate the process we started
        if "dictation" in running_processes:
            process = running_processes["dictation"]
            try:
                process.terminate()
                process.wait(timeout=5)
                logger.info("Dictation service process terminated")
            except subprocess.TimeoutExpired:
                # Force kill if terminate doesn't work
                process.kill()
                logger.info("Dictation service process force killed")
            del running_processes["dictation"]
            return "Dictation service stopped successfully"
        
        # If we don't have the process, try killing by port
        kill_process_on_port(5443)
        logger.info("Dictation service stopped (port-based kill)")
        return "Dictation service stopped successfully"
    except Exception as e:
        raise Exception(f"Dictation shutdown failed: {str(e)}")


def start_pacs_service() -> str:
    """Start the PACS service"""
    try:
        # Start the PACS backend (NASIntegration Flask app)
        pacs_path = Path("C:/Users/Admin/Desktop/ELC/Ubuntu-Patient-Care/4-PACS-Module/Orthanc/orthanc-source/NASIntegration/backend")
        
        if not pacs_path.exists():
            raise FileNotFoundError(f"PACS backend not found at {pacs_path}")
        
        import platform
        import time
        
        if platform.system() == "Windows":
            # Use py command for proper Python execution on Windows
            cmd = f'cd /d "{pacs_path}" && py app.py'
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=None,  # Allow console output to be visible
                stderr=None,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            # Use python3 on Unix/Linux
            process = subprocess.Popen(
                ["python3", "app.py"],
                cwd=str(pacs_path),
                stdout=None,
                stderr=None,
                preexec_fn=os.setsid
            )
        
        # Give it a moment to start
        time.sleep(0.5)
        
        # Check if process is still alive
        poll = process.poll()
        if poll is not None:
            raise Exception(f"Process exited immediately with code {poll}. Check if Python is installed and in PATH.")
        
        # Store process reference
        running_processes["pacs"] = process
        logger.info(f"PACS service started with PID: {process.pid}")
        return f"PACS service started (PID: {process.pid}). Check the console window for startup logs..."
    except Exception as e:
        logger.error(f"PACS startup error: {str(e)}")
        raise Exception(f"PACS startup failed: {str(e)}")


def stop_pacs_service() -> str:
    """Stop the PACS service"""
    try:
        # First try to terminate the process we started
        if "pacs" in running_processes:
            process = running_processes["pacs"]
            try:
                process.terminate()
                process.wait(timeout=5)
                logger.info("PACS service process terminated")
            except subprocess.TimeoutExpired:
                # Force kill if terminate doesn't work
                process.kill()
                logger.info("PACS service process force killed")
            del running_processes["pacs"]
            return "PACS service stopped successfully"
        
        # If we don't have the process, try killing by port
        kill_process_on_port(5000)
        logger.info("PACS service stopped (port-based kill)")
        return "PACS service stopped successfully"
    except Exception as e:
        raise Exception(f"PACS shutdown failed: {str(e)}")


def start_ris_service() -> str:
    """Start the RIS service (Node.js backend on port 3001)"""
    try:
        # Start the RIS backend (Express.js server)
        ris_backend_path = Path("C:/Users/Admin/Desktop/ELC/Ubuntu-Patient-Care/1-RIS-Module/sa-ris-backend")
        
        if not ris_backend_path.exists():
            raise FileNotFoundError(f"RIS backend not found at {ris_backend_path}")
        
        import platform
        
        if platform.system() == "Windows":
            # On Windows, use shell=True with cmd.exe to ensure npm is found in PATH
            cmd = f'cd /d "{ris_backend_path}" && npm start'
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=None,  # Allow console output to be visible
                stderr=None,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            process = subprocess.Popen(
                ["npm", "start"],
                cwd=str(ris_backend_path),
                stdout=None,
                stderr=None,
                preexec_fn=os.setsid
            )
        
        # Give it a moment to start
        import time
        time.sleep(0.5)
        
        # Check if process is still alive
        poll = process.poll()
        if poll is not None:
            raise Exception(f"Process exited immediately with code {poll}. Check if npm is installed and in PATH.")
        
        running_processes["ris"] = process
        logger.info(f"RIS backend service started with PID: {process.pid}")
        return f"RIS backend service started (PID: {process.pid}). Check the console window for output."
    except Exception as e:
        logger.error(f"RIS startup error: {str(e)}")
        raise Exception(f"RIS startup failed: {str(e)}")


def stop_ris_service() -> str:
    """Stop the RIS service"""
    try:
        # First try to terminate the process we started
        if "ris" in running_processes:
            process = running_processes["ris"]
            try:
                process.terminate()
                process.wait(timeout=5)
                logger.info("RIS backend process terminated")
            except subprocess.TimeoutExpired:
                process.kill()
                logger.info("RIS backend process force killed")
            del running_processes["ris"]
            return "RIS service stopped successfully"
        
        # If we don't have the process, try killing by port
        kill_process_on_port(3001)
        logger.info("RIS service stopped (port-based kill)")
        return "RIS service stopped successfully"
    except Exception as e:
        raise Exception(f"RIS shutdown failed: {str(e)}")


def start_billing_service() -> str:
    """Start the billing service (React frontend on port 3000)"""
    try:
        # Start the RIS frontend (React app)
        billing_path = Path("C:/Users/Admin/Desktop/ELC/Ubuntu-Patient-Care/1-RIS-Module/sa-ris-frontend")
        
        if not billing_path.exists():
            raise FileNotFoundError(f"Billing/RIS frontend not found at {billing_path}")
        
        import platform
        import time
        
        if platform.system() == "Windows":
            # On Windows, use shell=True to handle npm in PATH and env variables
            cmd = f'cd /d "{billing_path}" && set BROWSER=none && npm start'
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=None,  # Allow console output to be visible
                stderr=None,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            env = os.environ.copy()
            env["BROWSER"] = "none"
            process = subprocess.Popen(
                ["npm", "start"],
                cwd=str(billing_path),
                stdout=None,
                stderr=None,
                preexec_fn=os.setsid,
                env=env
            )
        
        # Give it a moment to start
        time.sleep(0.5)
        
        # Check if process is still alive
        poll = process.poll()
        if poll is not None:
            raise Exception(f"Process exited immediately with code {poll}. Check if npm is installed and in PATH.")
        
        running_processes["billing"] = process
        logger.info(f"Billing/Frontend service started with PID: {process.pid}")
        return f"Billing/Frontend service started (PID: {process.pid}). Check the console window for output."
    except Exception as e:
        logger.error(f"Billing startup error: {str(e)}")
        raise Exception(f"Billing startup failed: {str(e)}")


def stop_billing_service() -> str:
    """Stop the billing service"""
    try:
        # First try to terminate the process we started
        if "billing" in running_processes:
            process = running_processes["billing"]
            try:
                process.terminate()
                process.wait(timeout=5)
                logger.info("Billing/Frontend process terminated")
            except subprocess.TimeoutExpired:
                process.kill()
                logger.info("Billing/Frontend process force killed")
            del running_processes["billing"]
            return "Billing service stopped successfully"
        
        # If we don't have the process, try killing by port
        kill_process_on_port(3000)
        logger.info("Billing service stopped (port-based kill)")
        return "Billing service stopped successfully"
    except Exception as e:
        raise Exception(f"Billing shutdown failed: {str(e)}")


def kill_process_on_port(port: int) -> bool:
    """Kill process running on a specific port"""
    try:
        for conn in psutil.net_connections():
            if conn.laddr.port == port and conn.status == 'LISTEN':
                try:
                    process = psutil.Process(conn.pid)
                    # Try terminate first
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                        logger.info(f"Terminated process {conn.pid} on port {port}")
                    except psutil.TimeoutExpired:
                        # Force kill if terminate doesn't work
                        process.kill()
                        logger.info(f"Force killed process {conn.pid} on port {port}")
                    return True
                except Exception as e:
                    logger.error(f"Error killing process {conn.pid}: {str(e)}")
                    continue
        return False
    except Exception as e:
        logger.error(f"Failed to kill process on port {port}: {str(e)}")
        return False
