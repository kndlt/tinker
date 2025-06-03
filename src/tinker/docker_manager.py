import os
import subprocess

CONTAINER_NAME = "tinker_sandbox"
TINKER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.tinker'))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))


def ensure_tinker_dir():
    os.makedirs(TINKER_DIR, exist_ok=True)


def container_exists():
    result = subprocess.run([
        "docker", "ps", "-a", "--filter", f"name={CONTAINER_NAME}", "--format", "{{.Names}}"
    ], capture_output=True, text=True)
    return CONTAINER_NAME in result.stdout.strip().splitlines()


def container_running():
    result = subprocess.run([
        "docker", "ps", "--filter", f"name={CONTAINER_NAME}", "--format", "{{.Names}}"
    ], capture_output=True, text=True)
    return CONTAINER_NAME in result.stdout.strip().splitlines()


def start_container():
    ensure_tinker_dir()
    # Create workspace directory
    tinker_workspace_dir = os.path.join(TINKER_DIR, "workspace")
    os.makedirs(tinker_workspace_dir, exist_ok=True)
    
    # Use docker-compose to start the container
    if not container_exists():
        subprocess.run([
            "docker", "compose", "up", "-d"
        ], cwd=PROJECT_ROOT, check=True)
    elif not container_running():
        subprocess.run([
            "docker", "compose", "start"
        ], cwd=PROJECT_ROOT, check=True)


def exec_in_container(cmd):
    full_cmd = ["docker", "exec", CONTAINER_NAME] + cmd
    return subprocess.run(full_cmd, capture_output=True, text=True)


def stop_container():
    if container_running():
        subprocess.run([
            "docker", "compose", "stop"
        ], cwd=PROJECT_ROOT, check=True)


def remove_container():
    if container_exists():
        subprocess.run([
            "docker", "compose", "down"
        ], cwd=PROJECT_ROOT, check=True)
