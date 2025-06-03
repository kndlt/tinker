# GitHub Authentication Flow Fixes

## Issues Identified and Fixed

### 1. **Critical: Environment Variables Not Passed to Container**
**Problem:** The `GITHUB_TOKEN` from `.env` file was not being passed to the Docker container.
**Fix:** Added `env_file: - .env` to `docker-compose.yml` to automatically load environment variables.

### 2. **SSH Directory Path Inconsistency**
**Problem:** Code referenced both `.tinker/ssh/` and `.tinker/workspace/.ssh/` directories.
**Fix:** Standardized on `.tinker/workspace/.ssh/` since workspace is mounted in container.

### 3. **Redundant SSH Directory Creation**
**Problem:** `ensure_tinker_dir()` was creating a separate `ssh` directory that wasn't used.
**Fix:** Removed redundant SSH directory creation, rely on workspace mounting.

### 4. **Repetitive Authentication Checks**
**Problem:** Every GitHub function had identical container and auth status checks.
**Fix:** Created `_ensure_github_cli_ready()` helper function to reduce code duplication.

### 5. **Inconsistent Error Messages**
**Problem:** Error messages referenced different command formats (`tinker github-setup` vs `tinker --github-setup`).
**Fix:** Standardized all error messages to use the correct `--github-setup` format.

### 6. **Incomplete Token Setup Instructions**
**Problem:** Instructions didn't mention required GitHub token scopes or container restart.
**Fix:** Added detailed setup instructions with required scopes and restart steps.

### 7. **Missing Container Restart Function**
**Problem:** No easy way to restart container when environment variables change.
**Fix:** Added `restart_container()` function for when `.env` file is updated.

## Files Modified

- `docker-compose.yml` - Added env_file configuration
- `src/tinker/docker_manager.py` - Fixed SSH paths, added restart function
- `src/tinker/github_manager.py` - Reduced code duplication, improved error messages
- `.env.example` - Added detailed GITHUB_TOKEN documentation
- `README.md` - Updated setup instructions

## Testing the Fixes

After these changes, the authentication flow should work as follows:

1. **Token-based (Recommended):**
   ```bash
   # Add token to .env file
   echo "GITHUB_TOKEN=your_token_here" >> .env
   
   # Restart container to load new environment
   docker compose restart
   
   # Setup GitHub CLI
   poetry run tinker --github-setup
   ```

2. **Interactive:**
   ```bash
   docker exec -it tinker_sandbox gh auth login
   ```

3. **Test authentication:**
   ```bash
   poetry run tinker --github-status
   poetry run tinker --github-issues owner/repo
   ```

## Benefits

- ✅ Eliminates environment variable issues
- ✅ Reduces code duplication by ~60 lines
- ✅ Provides clearer error messages and setup instructions
- ✅ Fixes directory path inconsistencies
- ✅ Makes the codebase more maintainable
