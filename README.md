# [Top Secret] Tinker Project

Tinker is an autonomous AI agent that builds and maintains AI agents. Currently serving as a virtual engineer at Sprited, Tinker's main job is to build and maintain Pixel (the company's main public-facing AI).

## Features

✅ **Phase 1 (MVP) - COMPLETED**
- OpenAI chat API integration
- CLI tool that runs continuously 
- Creates `.tinker` folder for autonomous operations
- Generates activity every 5 seconds
- Graceful shutdown with Ctrl+C

✅ **Phase 2 - COMPLETED**
- Task-based workflow system
- Automatic task pickup from `.tinker/tasks/` folder
- Task state management (tasks → ongoing → done)
- Real-time state tracking in `.tinker/state.md`
- Process locking to prevent multiple instances

✅ **Phase 3 - COMPLETED**
- AI-powered task analysis using OpenAI
- Shell command execution capabilities
- User approval system for all shell commands
- Command editing and modification
- Detailed task completion reports
- Safe command execution with timeouts

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

### Basic Usage

Once started, Tinker will:
- Create a `.tinker` folder in the current directory with subfolders: `tasks/`, `ongoing/`, `done/`
- Load environment variables from `.env` file (if present)
- Initialize the OpenAI client for Phase 3 AI capabilities
- Scan for tasks in `.tinker/tasks/` every 5 seconds
- Process tasks with AI analysis and shell command execution (Phase 3)
- Move completed tasks to `.tinker/done/` with detailed reports

To stop Tinker, press `Ctrl+C` for a graceful shutdown.

### Phase 3: AI-Powered Task Execution

**Creating Tasks:**
1. Create `.md` files in `.tinker/tasks/` folder
2. Describe what you want Tinker to accomplish
3. Tinker will analyze the task and propose shell commands if needed

**Shell Command Flow:**
1. AI analyzes the task content
2. If shell commands are needed, Tinker shows:
   - Reasoning for why commands are needed
   - List of suggested commands
3. User approves, rejects, or edits each command
4. Approved commands are executed with full output capture
5. Detailed completion report is generated

**Example Task File** (`.tinker/tasks/setup_project.md`):
```markdown
# Setup New Python Project

Create a new Python project structure with:
- src/ directory
- tests/ directory  
- requirements.txt file
- Basic README.md

Initialize git repository and make initial commit.
```

**Safety Features:**
- All shell commands require explicit user approval
- Commands can be modified before execution
- 30-second timeout prevents hanging processes
- Conservative AI suggestions prioritize safety
- Detailed logging of all operations

## Project Structure

```
tinker/
├── src/tinker/
│   ├── __init__.py
│   └── main.py           # Main CLI with Phase 3 capabilities
├── docs/
│   ├── phase1.md         # Phase 1 requirements (completed)
│   ├── phase2.md         # Phase 2 requirements (completed)  
│   └── phase3.md         # Phase 3 requirements (completed)
├── demo_phase3.py        # Demo script for Phase 3 testing
├── pyproject.toml        # Poetry configuration
└── README.md
```

**Generated Structure** (when Tinker runs):
```
.tinker/
├── tasks/                # Place task files here (.md format)
├── ongoing/              # Tasks currently being processed
├── done/                 # Completed tasks with reports
├── state.md              # Real-time state tracking
└── tinker.lock           # Process lock file
```

## Testing Phase 3

Run the demo setup script to create sample tasks:

```bash
python demo_phase3.py
```

This creates sample tasks that demonstrate:
- File creation with shell commands
- Directory structure setup
- Analysis tasks (no shell commands needed)

Then start Tinker to process them:

```bash
poetry run tinker
```