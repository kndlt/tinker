# Tinker Project

Tinker is an autonomous AI agent that builds and maintains AI agents. Currently serving as a virtual engineer at Sprited, Tinker's main job is to build and maintain Pixel (the company's main public-facing AI).

## Setup

### 1. Install Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Install Docker

- On macOS, you can use Homebrew:
  ```sh
  brew install --cask docker
  open /Applications/Docker.app
  # Wait for Docker to finish starting (check the menu bar whale icon)
  ```
- Or download Docker Desktop from https://www.docker.com/products/docker-desktop/ (macOS/Windows)
- For Linux, follow: https://docs.docker.com/engine/install/
- Verify installation (Docker Compose is included with Docker Desktop):
  ```sh
  docker --version
  docker compose version
  ```

### 3. Clone the repo and install

```bash
git clone https://github.com/kndlt/tinker.git
cd tinker
poetry install
```

### 4. Set up OpenAI API Key

Create a `.env` file in the project root:

```bash
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

Or set it as an environment variable:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 5. Run Tinker

```bash
poetry run tinker
```

Or enter Poetry shell:

```bash
poetry shell
tinker
```

## GitHub SSH Authentication

Tinker automatically sets up SSH authentication for GitHub when it starts for the first time. This enables secure git operations within the Docker container.

### Automatic Setup

When you first run Tinker, it will:
1. 🔑 Generate an ED25519 SSH key pair
2. 📋 Display the public key for you to add to GitHub
3. ⏳ Wait for you to add the key to your GitHub account
4. 🔍 Test the SSH connection
5. ✅ Configure git to use SSH for GitHub repositories

### Manual SSH Management

You can also manage SSH authentication manually:

```bash
# Check SSH status
poetry run tinker --ssh-status
# or
./tinker-ssh status

# Setup/reset SSH authentication
poetry run tinker --ssh-setup
# or  
./tinker-ssh setup

# Reset and regenerate SSH keys
poetry run tinker --ssh-reset
# or
./tinker-ssh reset
```

### Adding SSH Key to GitHub

1. Go to [GitHub SSH Settings](https://github.com/settings/ssh/new)
2. Give it a title like "Tinker Docker Container"  
3. Paste the public key that Tinker displays
4. Click "Add SSH key"

The SSH key will be stored in `.tinker/ssh/` and mounted into the Docker container at `/home/tinker/.ssh/`.

