# Tinker - Phase 4

In Phase 3, we added a feature for Tinker to interface with shell (with approval prompt). I'm not comfortable with running anything like this. Too scary. It could do `rm -rf` on things I don't want deleted.

In Phase 4, let's find a way to do this little more safely. When the process runs, could you run docker?

I want to do something like this.

- When tinker starts, it will start a docker container. 
- It is persistent one. So if you turn it off, it can still be brought back up next time tinker runs.
- docker instance can live within .tinker folder.

## Phase 4 Tasks

- [ ] Research best practices for running untrusted code safely using Docker
- [ ] Define the Docker image and environment for Tinker tasks
- [ ] Update Tinker to start a persistent Docker container on launch
- [ ] Ensure the Docker container is tied to the .tinker folder (for data persistence)
- [ ] Implement logic to reuse or restart the container if it already exists
- [ ] Route all shell/task execution through the Docker container
- [ ] Add user documentation for Docker-based execution and safety
- [ ] Test the new workflow to ensure tasks run only inside Docker
- [ ] Add fallback or error handling if Docker is unavailable