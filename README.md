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
