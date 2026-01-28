# 🎯 SINGLE SOURCE OF TRUTH (SSOT)

## Persistent Task Management for AI-Driven Development

**Solves the 3 biggest problems in AI-assisted development:**
1. ❌ Session crashes → Context lost
2. ❌ Token exhaustion → New session forgets state
3. ❌ Multi-session workflows → Inconsistent context

**Solution:** File-based persistent task lists as the **SINGLE SOURCE OF TRUTH**.

---

## 🚀 Quick Start

```bash
# Install
pip install pydantic

# Create a pipeline
python -m src.cli create 2026-01-28 --count 23

# Resume after crash
python -m src.cli resume

# Check status
python -m src.cli status
```

---

## 📋 The Problem

### Before SSOT (Every New Session):
```
┌─────────────────────────────────────────────┐
│ "What were we working on?"                  │
│ → Search memory (incomplete)                │
│ → Search past chats (fragmented)            │
│ → Fetch PROJECT_STATE.json (stale?)         │
│ → Rebuild mental model (5-10 min)           │
│ → MAYBE get back to where we were           │
└─────────────────────────────────────────────┘
```

### After SSOT:
```
┌─────────────────────────────────────────────┐
│ "Continue task list"                        │
│ → Read .claude/tasks/biddeed-pipeline.json  │
│ → Task 3 of 7: IN_PROGRESS                  │
│ → Dependencies: Tasks 1,2 ✅ COMPLETED      │
│ → Context: Embedded in task metadata        │
│ → INSTANT resume. Zero reconstruction.      │
└─────────────────────────────────────────────┘
```

---

## 🏗️ Architecture

```
.claude/tasks/
├── auction-2026-01-28.json    # Task list (SINGLE SOURCE OF TRUTH)
├── auction-2026-01-29.json    # Another task list
└── ...

Each task list contains:
├── Metadata (name, created_at, session_id)
├── Global context (shared state across tasks)
└── Tasks[]
    ├── id, title, status
    ├── depends_on (dependency graph)
    ├── checkpoint (crash recovery point)
    │   ├── progress_pct
    │   ├── current_item
    │   ├── items_completed/total
    │   └── context (task-specific state)
    └── output (results when completed)
```

---

## 🔧 BidDeed.AI 12-Stage Pipeline

The system comes pre-configured for BidDeed.AI's foreclosure analysis pipeline:

| Stage | Task | Agent | Depends On |
|-------|------|-------|------------|
| 1 | Discovery | scraper_agent | - |
| 2 | Scraping | scraper_agent | Discovery |
| 3 | Title Search | scraper_agent | Scraping |
| 4 | Lien Priority | analysis_agent | Title Search |
| 5 | Tax Certs | scraper_agent | Scraping |
| 6 | Demographics | analysis_agent | Scraping |
| 7 | ML Scoring | ml_agent | Lien Priority, Demographics |
| 8 | Max Bid | analysis_agent | ML Score, Tax Certs |
| 9 | Decision Log | analysis_agent | Max Bid |
| 10 | Report | report_agent | Decision Log |
| 11 | Disposition | operations_agent | Report |
| 12 | Archive | operations_agent | Disposition |

---

## 💻 Python API

```python
from src import TaskManager

# Initialize
manager = TaskManager(tasks_dir=".claude/tasks")

# Create pipeline for auction
task_list = manager.create_biddeed_pipeline(
    auction_date="2026-01-28",
    property_count=23
)

# Start task
manager.start_task("t01")

# Update checkpoint (for crash recovery)
manager.update_checkpoint(
    task_id="t01",
    progress_pct=50,
    current_item="parcel_2612345",
    items_completed=12,
    items_total=23,
    context={"last_api_call": "bcpao", "retry_count": 0}
)

# Complete task
manager.complete_task("t01", output={
    "properties_found": 23,
    "data_source": "realforeclose"
})

# After crash - INSTANT RESUME
result = manager.resume()
print(manager.get_resume_prompt())

# Output:
# ============================================================
# 📋 SINGLE SOURCE OF TRUTH - SESSION RESUME
# ============================================================
# Task List: auction-2026-01-28
# Progress: 8%
# 
# 🔄 RESUME TASK:
#    ID: t02
#    Title: Property Data Scraping
#    Stage: scraping
#    Progress: 50%
#    Current Item: parcel_2612345
#    Completed: 12/23
```

---

## 🖥️ CLI Commands

```bash
# Create new pipeline
ssot create 2026-01-28 --count 23

# Resume from crash (finds most recent task list)
ssot resume

# Resume specific task list
ssot resume auction-2026-01-28

# Check status
ssot status
ssot status --json

# Start a task
ssot start t01

# Update checkpoint
ssot checkpoint t01 -p 50 -i parcel_123 --completed 12 --total 23

# Complete task
ssot complete t01 --output '{"count": 23}'

# Mark task as failed
ssot fail t01 --error "API timeout"

# List all task lists
ssot list
ssot list --json
```

---

## 🔄 Multi-Agent Coordination

SSOT enables multi-agent orchestration by providing a shared contract:

```python
# Agent A completes task
manager.complete_task("t01", output={"properties": 23})

# Agent B sees dependency resolved, starts next task
result = manager.resume()
for task in result["next_tasks"]:
    if task.assigned_agent == "scraper_agent":
        manager.start_task(task.id)
        # Execute task...
```

### LangGraph Integration

```python
from langgraph.graph import StateGraph
from src import TaskManager

def agent_node(state):
    manager = TaskManager()
    result = manager.resume()
    
    if result["resume_task"]:
        # Continue from checkpoint
        task = result["resume_task"]
        checkpoint = result["checkpoint"]
        # Resume at checkpoint.current_item
    else:
        # Start next available task
        for task in result["next_tasks"]:
            if task.assigned_agent == state["agent_name"]:
                manager.start_task(task.id)
                break
    
    return state
```

---

## 📁 File Structure

```
ssot-task-manager/
├── src/
│   ├── __init__.py      # Package exports
│   ├── schema.py        # Task schema definitions
│   ├── manager.py       # TaskManager core logic
│   └── cli.py           # Command-line interface
├── .claude/
│   └── tasks/           # Task list storage (SSOT)
│       ├── auction-2026-01-28.json
│       └── ...
├── requirements.txt
└── README.md
```

---

## 🔒 Task States

| State | Icon | Description |
|-------|------|-------------|
| PENDING | ⬜ | Not started |
| IN_PROGRESS | 🔵 | Currently executing |
| BLOCKED | 🟡 | Waiting on dependencies |
| COMPLETED | ✅ | Successfully finished |
| FAILED | ❌ | Error occurred |
| SKIPPED | ⏭️ | Intentionally bypassed |
| DEFERRED | 📅 | Postponed for later |

---

## ⚡ Key Features

### 1. Crash Recovery
```python
# Before crash
manager.update_checkpoint("t03", 
    progress_pct=67,
    current_item="parcel_2612999",
    items_completed=15,
    items_total=23
)

# After crash
result = manager.resume()
# Instantly at parcel_2612999, 15/23 done
```

### 2. Dependency Management
```python
# Task t04 (Lien Priority) depends on t03 (Title Search)
manager.start_task("t04")
# ⛔ Task t04 blocked by: ['t03']

# Complete dependency
manager.complete_task("t03")
# 🔓 Unblocked task: Lien Priority Analysis

manager.start_task("t04")  # Now works
```

### 3. Session Continuity
```python
# Session 1: Start work
manager.start_task("t01")
manager.update_checkpoint("t01", progress_pct=30)
# Token limit hit - session ends

# Session 2: Instant resume
result = manager.resume()
# Task t01 at 30%, ready to continue
```

---

## 🔗 Integration Points

### Supabase (Backup Only)
```python
from supabase import create_client

supabase = create_client(url, key)
manager = TaskManager(supabase_client=supabase)

# File system is SSOT, Supabase is backup
manager.save(task_list)  # Saves to both
```

### GitHub Actions
```yaml
- name: Resume pipeline
  run: |
    python -m src.cli resume
    python -m src.cli status --json > status.json
```

---

## 🚫 Deprecates

This system replaces:
- ❌ Ralph Wiggum sprint_tasks table
- ❌ Complex boot sequences (Memory → recent_chats → Supabase → PROJECT_STATE.json)
- ❌ Manual context reconstruction
- ❌ Supabase checkpoints for task state

**New reality:** `.claude/tasks/` is the SINGLE SOURCE OF TRUTH.

---

## 📜 License

MIT License - BidDeed.AI / Everest Capital USA

---

## 🏆 Credits

Inspired by Claude Code's native task list feature as analyzed by Manus AI.
Built for the BidDeed.AI agentic foreclosure analysis platform.
