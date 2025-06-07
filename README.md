# Tinker Project

Tinker is an interactive AI agent that helps you with development tasks. Chat naturally with Tinker to get help with coding, debugging, file operations, and more.

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

### 4. Set up Anthropic API Key

Create a `.env` file in the project root:

```bash
echo "ANTHROPIC_API_KEY=your-api-key-here" > .env
```

Or set it as an environment variable:

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

### 5. Run Tinker

Start interactive chat mode (default):
```bash
poetry run tinker
```

Or process a single task:
```bash
poetry run tinker "check the git status"
```

You can also enter Poetry shell:
```bash
poetry shell
tinker
```

## Usage

Tinker provides an interactive chat interface where you can:

- **Ask questions**: "What files are in this directory?"
- **Give tasks**: "Create a new Python file called test.py"
- **Debug issues**: "Why is my code failing?"
- **Get help**: "How do I set up a virtual environment?"

### Example Session

```
🧪 tinker> what's in the current directory?
🤖 Let me check the current directory contents for you.
🔧 Actions taken:
   Dockerfile  README.md  config/  demo_phase_5_1.py  docker-compose.yml  docs/  ...

🧪 tinker> create a simple hello world python script
🤖 I'll create a simple "Hello World" Python script for you.
🔧 Actions taken:
   Created hello.py with a simple print statement

🧪 tinker> exit
👋 Goodbye!
```

### Exit Commands

Type any of these to exit:
- `exit`
- `quit` 
- `bye`
- Ctrl+C

## Persistent Memory

Tinker remembers your conversations across sessions! When you restart Tinker, it will continue from where you left off, maintaining context about:

- Previous questions and answers
- Tasks you've completed
- Code you've been working on
- Project context and history

The conversation history is stored in `.tinker/memory.db` and automatically loads when you start Tinker.

### Memory Indicators

- 🆕 **Starting new conversation...** - First time using Tinker
- 🧠 **Continuing previous conversation...** - Resuming from previous session

