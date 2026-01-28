"""
SINGLE SOURCE OF TRUTH (SSOT) - Task Management System
=======================================================

Persistent task management for AI-driven development workflows.
Solves: Session crashes, token exhaustion, context inconsistency.

Usage:
    from ssot import TaskManager
    
    manager = TaskManager()
    manager.create_biddeed_pipeline("2026-01-28", property_count=23)
    
    # Start working
    manager.start_task("t01")
    manager.update_checkpoint("t01", progress_pct=50, current_item="parcel_123")
    manager.complete_task("t01", output={"properties": 23})
    
    # After crash - resume exactly where you left off
    result = manager.resume()
    print(manager.get_resume_prompt())

Author: BidDeed.AI / Everest Capital USA
"""

from .schema import (
    TaskList,
    Task,
    TaskStatus,
    TaskPriority,
    TaskCheckpoint,
    BIDDEED_PIPELINE_STAGES,
    create_biddeed_task_list
)

from .manager import TaskManager

__version__ = "1.0.0"
__all__ = [
    "TaskManager",
    "TaskList",
    "Task",
    "TaskStatus",
    "TaskPriority",
    "TaskCheckpoint",
    "BIDDEED_PIPELINE_STAGES",
    "create_biddeed_task_list"
]
