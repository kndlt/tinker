# Tinker Phase 1.4: Docker-based Shell Execution

All shell/task execution is now routed through a persistent Docker container for safety using Docker Compose.

## How to Use

- On Tinker startup, a Docker container is created (or reused) using Docker Compose and persists between runs.
- The container uses the `.tinker/workspace` folder for persistent workspace data.
- All shell commands are executed inside the container using `docker exec`.
- If Docker is unavailable, Tinker will not run shell commands and will exit for safety.

## Configuration

The Docker environment is defined in `docker-compose.yml` at the project root, which provides:
- A Python 3.12 slim container
- Automatic restart policy
- Volume mount of `.tinker/workspace` to `/workspace` in the container
- Working directory set to `/workspace`

## Safety Notes
- The container is isolated from your host system, reducing risk from untrusted code.
- Only the `.tinker/workspace` folder is mounted for persistence.
- You can stop or remove the container manually with:
  - `docker compose stop` (from project root)
  - `docker compose down` (from project root)

## Troubleshooting
- Ensure Docker and Docker Compose are installed and running on your system.
- If you encounter issues, check Docker logs with `docker compose logs` or restart Docker.
