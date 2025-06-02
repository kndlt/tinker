# [Top Secret] Tinker Project

Tinker is an autonomous AI agent that builds and maintains AI agents. Currently serving as a virtual engineer at Sprited, Tinker's main job is to build and maintain Pixel (the company's main public-facing AI).

## Features

✅ **Phase 1 (MVP) - COMPLETED**
- OpenAI chat API integration
- CLI tool that runs continuously 
- Creates `.tinker` folder for autonomous operations
- Generates activity every 5 seconds
- Graceful shutdown with Ctrl+C

## Setup

### 1. Install Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Clone the repo and install

```bash
git clone https://github.com/kndlt/tinker.git
cd tinker
poetry install
```

### 3. Set up OpenAI API Key

Create a `.env` file in the project root:

```bash
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

Or set it as an environment variable:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 4. Run Tinker

```bash
poetry run tinker
```

Or enter Poetry shell:

```bash
poetry shell
tinker
```

## Usage

Once started, Tinker will:
- Create a `.tinker` folder in the current directory
- Load environment variables from `.env` file (if present)
- Initialize the OpenAI client
- Run continuously, generating activity every 5 seconds
- Display timestamped output of its operations

To stop Tinker, press `Ctrl+C` for a graceful shutdown.

## Project Structure

```
tinker/
├── src/tinker/
│   ├── __init__.py
│   └── main.py           # Main CLI entry point
├── docs/
│   └── phase1.md         # Phase 1 requirements and status
├── pyproject.toml        # Poetry configuration
└── README.md
```