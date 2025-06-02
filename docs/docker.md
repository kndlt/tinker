# Tinker Phase 4: Docker-based Shell Execution

All shell/task execution is now routed through a persistent Docker container for safety.

## How to Use

- On Tinker startup, a Docker container is created (or reused) and persists between runs.
- The container uses the `.tinker` folder for persistent workspace data.
- All shell commands are executed inside the container using `docker exec`.
- If Docker is unavailable, Tinker will not run shell commands and will exit for safety.

## Safety Notes
- The container is isolated from your host system, reducing risk from untrusted code.
- Only the `.tinker` folder is mounted for persistence.
- You can stop or remove the container manually with:
  - `docker stop tinker_sandbox`
  - `docker rm tinker_sandbox`

## Troubleshooting
- Ensure Docker is installed and running on your system.
- If you encounter issues, check Docker logs or restart Docker.
