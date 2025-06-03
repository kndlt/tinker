import os
import subprocess

DOCKER_IMAGE = "python:3.12-slim"  # You can customize this
CONTAINER_NAME = "tinker_sandbox"
TINKER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.tinker'))


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
    # Mount only the .tinker/workspace directory from the project root into the container as /workspace
    tinker_workspace_dir = os.path.join(TINKER_DIR, "workspace")
    os.makedirs(tinker_workspace_dir, exist_ok=True)
    if not container_exists():
        subprocess.run([
            "docker", "run", "-d",
            "--name", CONTAINER_NAME,
            "-v", f"{tinker_workspace_dir}:/workspace",
            "-w", "/workspace",
            DOCKER_IMAGE,
            "tail", "-f", "/dev/null"
        ], check=True)
    elif not container_running():
        subprocess.run(["docker", "start", CONTAINER_NAME], check=True)


def exec_in_container(cmd):
    full_cmd = ["docker", "exec", CONTAINER_NAME] + cmd
    return subprocess.run(full_cmd, capture_output=True, text=True)


def stop_container():
    if container_running():
        subprocess.run(["docker", "stop", CONTAINER_NAME], check=True)


def remove_container():
    if container_exists():
        subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], check=True)
