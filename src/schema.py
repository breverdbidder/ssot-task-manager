"""
SINGLE SOURCE OF TRUTH (SSOT) - Task Schema Definition
=======================================================
Persistent task management for AI-driven development workflows.
Solves: Session crashes, token exhaustion, context inconsistency.

Author: BidDeed.AI / Everest Capital USA
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class TaskStatus(str, Enum):
    """Task lifecycle states"""
    PENDING = "pending"           # Not started
    IN_PROGRESS = "in_progress"   # Currently executing
    BLOCKED = "blocked"           # Waiting on dependencies
    COMPLETED = "completed"       # Successfully finished
    FAILED = "failed"             # Error occurred
    SKIPPED = "skipped"           # Intentionally bypassed
    DEFERRED = "deferred"         # Postponed for later


class TaskPriority(str, Enum):
    """Task priority levels"""
    CRITICAL = "critical"   # Must complete this session
    HIGH = "high"           # Important, complete soon
    MEDIUM = "medium"       # Normal priority
    LOW = "low"             # Nice to have


class TaskCheckpoint(BaseModel):
    """Checkpoint for resuming interrupted tasks"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    progress_pct: int = Field(ge=0, le=100, default=0)
    current_item: Optional[str] = None  # e.g., "parcel_2612345"
    items_completed: int = 0
    items_total: int = 0
    context: Dict[str, Any] = Field(default_factory=dict)  # Task-specific state
    notes: Optional[str] = None


class Task(BaseModel):
    """Individual task definition"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    stage: str                      # Pipeline stage name
    title: str                      # Human-readable title
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    
    # Dependencies
    depends_on: List[str] = Field(default_factory=list)  # Task IDs
    blocks: List[str] = Field(default_factory=list)      # Task IDs this blocks
    
    # Execution tracking
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_minutes: Optional[int] = None
    actual_minutes: Optional[int] = None
    
    # Checkpointing for crash recovery
    checkpoint: Optional[TaskCheckpoint] = None
    
    # Output
    output: Optional[Dict[str, Any]] = None  # Results from task execution
    error: Optional[str] = None              # Error message if failed
    
    # Metadata
    assigned_agent: Optional[str] = None     # e.g., "scraper_agent", "analysis_agent"
    retry_count: int = 0
    max_retries: int = 3
    tags: List[str] = Field(default_factory=list)


class TaskList(BaseModel):
    """Complete task list - THE SINGLE SOURCE OF TRUTH"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str                       # e.g., "auction-2026-01-28"
    description: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = "claude-ai"
    
    # Pipeline info
    pipeline: str = "biddeed-12-stage"  # Pipeline template used
    
    # Tasks
    tasks: List[Task] = Field(default_factory=list)
    
    # Session tracking
    session_id: Optional[str] = None     # Current session working on this
    last_active_task_id: Optional[str] = None
    
    # Global state for cross-task data
    global_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Completion tracking
    @property
    def progress_pct(self) -> int:
        if not self.tasks:
            return 0
        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        return int((completed / len(self.tasks)) * 100)
    
    @property
    def status_summary(self) -> Dict[str, int]:
        summary = {status.value: 0 for status in TaskStatus}
        for task in self.tasks:
            summary[task.status.value] += 1
        return summary


# ============================================================
# BIDDEED.AI 12-STAGE PIPELINE TEMPLATE
# ============================================================

BIDDEED_PIPELINE_STAGES = [
    {
        "stage": "discovery",
        "title": "Auction Discovery",
        "description": "Fetch auction calendar from RealForeclose",
        "assigned_agent": "scraper_agent",
        "estimated_minutes": 5
    },
    {
        "stage": "scraping",
        "title": "Property Data Scraping", 
        "description": "Pull BCPAO parcel data, photos, and details",
        "depends_on": ["discovery"],
        "assigned_agent": "scraper_agent",
        "estimated_minutes": 15
    },
    {
        "stage": "title_search",
        "title": "Title Search",
        "description": "Search AcclaimWeb for recorded documents",
        "depends_on": ["scraping"],
        "assigned_agent": "scraper_agent",
        "estimated_minutes": 20
    },
    {
        "stage": "lien_priority",
        "title": "Lien Priority Analysis",
        "description": "Determine lien positions and survival analysis",
        "depends_on": ["title_search"],
        "assigned_agent": "analysis_agent",
        "estimated_minutes": 15
    },
    {
        "stage": "tax_certs",
        "title": "Tax Certificate Check",
        "description": "Check RealTDM for outstanding tax certificates",
        "depends_on": ["scraping"],
        "assigned_agent": "scraper_agent",
        "estimated_minutes": 10
    },
    {
        "stage": "demographics",
        "title": "Demographics Analysis",
        "description": "Pull Census API data for neighborhood context",
        "depends_on": ["scraping"],
        "assigned_agent": "analysis_agent",
        "estimated_minutes": 5
    },
    {
        "stage": "ml_score",
        "title": "ML Scoring",
        "description": "Run XGBoost model for third-party probability",
        "depends_on": ["lien_priority", "demographics"],
        "assigned_agent": "ml_agent",
        "estimated_minutes": 5
    },
    {
        "stage": "max_bid",
        "title": "Max Bid Calculation",
        "description": "Calculate (ARV×70%)-Repairs-$10K-MIN($25K,15%ARV)",
        "depends_on": ["ml_score", "tax_certs"],
        "assigned_agent": "analysis_agent",
        "estimated_minutes": 5
    },
    {
        "stage": "decision_log",
        "title": "Decision Logging",
        "description": "Generate BID/REVIEW/SKIP recommendations",
        "depends_on": ["max_bid"],
        "assigned_agent": "analysis_agent",
        "estimated_minutes": 5
    },
    {
        "stage": "report",
        "title": "Report Generation",
        "description": "Create DOCX reports with BCPAO photos",
        "depends_on": ["decision_log"],
        "assigned_agent": "report_agent",
        "estimated_minutes": 10
    },
    {
        "stage": "disposition",
        "title": "Disposition Tracking",
        "description": "Track auction outcomes and update history",
        "depends_on": ["report"],
        "assigned_agent": "operations_agent",
        "estimated_minutes": 5
    },
    {
        "stage": "archive",
        "title": "Archive Storage",
        "description": "Store completed analysis in Supabase",
        "depends_on": ["disposition"],
        "assigned_agent": "operations_agent",
        "estimated_minutes": 5
    }
]


def create_biddeed_task_list(
    auction_date: str,
    property_count: int = 0,
    session_id: Optional[str] = None
) -> TaskList:
    """Create a new BidDeed.AI pipeline task list"""
    
    task_list = TaskList(
        name=f"auction-{auction_date}",
        description=f"BidDeed.AI foreclosure analysis pipeline for {auction_date}",
        pipeline="biddeed-12-stage",
        session_id=session_id,
        global_context={
            "auction_date": auction_date,
            "property_count": property_count,
            "county": "brevard"
        }
    )
    
    # Create tasks from template
    task_id_map = {}  # stage -> task_id
    
    for i, stage_def in enumerate(BIDDEED_PIPELINE_STAGES):
        task = Task(
            id=f"t{i+1:02d}",
            stage=stage_def["stage"],
            title=stage_def["title"],
            description=stage_def.get("description"),
            assigned_agent=stage_def.get("assigned_agent"),
            estimated_minutes=stage_def.get("estimated_minutes")
        )
        task_id_map[stage_def["stage"]] = task.id
        task_list.tasks.append(task)
    
    # Resolve dependencies
    for task in task_list.tasks:
        stage_def = next(s for s in BIDDEED_PIPELINE_STAGES if s["stage"] == task.stage)
        if "depends_on" in stage_def:
            task.depends_on = [task_id_map[dep] for dep in stage_def["depends_on"]]
    
    # Calculate blocks (reverse of depends_on)
    for task in task_list.tasks:
        for dep_id in task.depends_on:
            dep_task = next(t for t in task_list.tasks if t.id == dep_id)
            if task.id not in dep_task.blocks:
                dep_task.blocks.append(task.id)
    
    return task_list
