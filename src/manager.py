"""
SINGLE SOURCE OF TRUTH (SSOT) - Task Manager
=============================================
Handles persistence, state transitions, and crash recovery.
File-based storage as primary. Supabase as backup/history.

Author: BidDeed.AI / Everest Capital USA
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from .schema import (
    TaskList, Task, TaskStatus, TaskCheckpoint,
    create_biddeed_task_list, BIDDEED_PIPELINE_STAGES
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ssot")


class TaskManager:
    """
    SINGLE SOURCE OF TRUTH Task Manager
    
    Primary storage: .claude/tasks/{task_list_id}.json
    Backup storage: Supabase (optional)
    
    Key features:
    - Crash recovery via checkpoints
    - Session continuity across token exhaustion
    - Multi-agent coordination
    """
    
    def __init__(
        self,
        tasks_dir: str = ".claude/tasks",
        supabase_client: Optional[Any] = None
    ):
        self.tasks_dir = Path(tasks_dir)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.supabase = supabase_client
        self._current_task_list: Optional[TaskList] = None
    
    # ========================================
    # PERSISTENCE OPERATIONS
    # ========================================
    
    def _get_task_file(self, task_list_id: str) -> Path:
        """Get path to task list JSON file"""
        return self.tasks_dir / f"{task_list_id}.json"
    
    def save(self, task_list: TaskList) -> None:
        """Save task list to file (SINGLE SOURCE OF TRUTH)"""
        task_list.updated_at = datetime.utcnow()
        
        file_path = self._get_task_file(task_list.id)
        with open(file_path, 'w') as f:
            json.dump(task_list.model_dump(mode='json'), f, indent=2, default=str)
        
        logger.info(f"✅ Saved task list: {task_list.id} ({task_list.progress_pct}% complete)")
        
        # Backup to Supabase if available
        if self.supabase:
            try:
                self._sync_to_supabase(task_list)
            except Exception as e:
                logger.warning(f"Supabase backup failed: {e}")
    
    def load(self, task_list_id: str) -> Optional[TaskList]:
        """Load task list from file"""
        file_path = self._get_task_file(task_list_id)
        
        if not file_path.exists():
            logger.warning(f"Task list not found: {task_list_id}")
            return None
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        task_list = TaskList(**data)
        self._current_task_list = task_list
        
        logger.info(f"📂 Loaded task list: {task_list.id} ({task_list.progress_pct}% complete)")
        return task_list
    
    def list_task_lists(self) -> List[Dict[str, Any]]:
        """List all available task lists"""
        task_lists = []
        
        for file_path in self.tasks_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                task_lists.append({
                    "id": data["id"],
                    "name": data["name"],
                    "progress": f"{self._calc_progress(data)}%",
                    "updated_at": data["updated_at"],
                    "status": self._get_overall_status(data)
                })
            except Exception as e:
                logger.warning(f"Error reading {file_path}: {e}")
        
        return sorted(task_lists, key=lambda x: x["updated_at"], reverse=True)
    
    def _calc_progress(self, data: dict) -> int:
        """Calculate progress from raw data"""
        tasks = data.get("tasks", [])
        if not tasks:
            return 0
        completed = sum(1 for t in tasks if t.get("status") == "completed")
        return int((completed / len(tasks)) * 100)
    
    def _get_overall_status(self, data: dict) -> str:
        """Determine overall status of task list"""
        tasks = data.get("tasks", [])
        if not tasks:
            return "empty"
        
        statuses = [t.get("status") for t in tasks]
        if all(s == "completed" for s in statuses):
            return "completed"
        if any(s == "in_progress" for s in statuses):
            return "in_progress"
        if any(s == "failed" for s in statuses):
            return "has_failures"
        return "pending"
    
    # ========================================
    # TASK OPERATIONS
    # ========================================
    
    def create_biddeed_pipeline(
        self,
        auction_date: str,
        property_count: int = 0,
        session_id: Optional[str] = None
    ) -> TaskList:
        """Create a new BidDeed.AI 12-stage pipeline"""
        task_list = create_biddeed_task_list(
            auction_date=auction_date,
            property_count=property_count,
            session_id=session_id or self._generate_session_id()
        )
        
        self.save(task_list)
        self._current_task_list = task_list
        
        logger.info(f"🚀 Created BidDeed pipeline: {task_list.name}")
        return task_list
    
    def start_task(self, task_id: str) -> Optional[Task]:
        """Start a task (sets status to in_progress)"""
        if not self._current_task_list:
            raise ValueError("No task list loaded")
        
        task = self._get_task(task_id)
        if not task:
            return None
        
        # Check dependencies
        blocked_by = self._get_blocking_dependencies(task)
        if blocked_by:
            logger.warning(f"⛔ Task {task_id} blocked by: {blocked_by}")
            task.status = TaskStatus.BLOCKED
            self.save(self._current_task_list)
            return task
        
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.utcnow()
        task.checkpoint = TaskCheckpoint(progress_pct=0)
        
        self._current_task_list.last_active_task_id = task_id
        self.save(self._current_task_list)
        
        logger.info(f"▶️ Started task: {task.title} ({task_id})")
        return task
    
    def update_checkpoint(
        self,
        task_id: str,
        progress_pct: int,
        current_item: Optional[str] = None,
        items_completed: int = 0,
        items_total: int = 0,
        context: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None
    ) -> None:
        """Update task checkpoint for crash recovery"""
        if not self._current_task_list:
            raise ValueError("No task list loaded")
        
        task = self._get_task(task_id)
        if not task:
            return
        
        task.checkpoint = TaskCheckpoint(
            progress_pct=progress_pct,
            current_item=current_item,
            items_completed=items_completed,
            items_total=items_total,
            context=context or {},
            notes=notes
        )
        
        self.save(self._current_task_list)
        logger.debug(f"💾 Checkpoint: {task_id} at {progress_pct}% ({current_item})")
    
    def complete_task(
        self,
        task_id: str,
        output: Optional[Dict[str, Any]] = None
    ) -> Optional[Task]:
        """Mark task as completed"""
        if not self._current_task_list:
            raise ValueError("No task list loaded")
        
        task = self._get_task(task_id)
        if not task:
            return None
        
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.output = output
        
        if task.started_at:
            task.actual_minutes = int(
                (task.completed_at - task.started_at).total_seconds() / 60
            )
        
        task.checkpoint = TaskCheckpoint(progress_pct=100)
        
        # Unblock dependent tasks
        self._update_blocked_tasks()
        
        self.save(self._current_task_list)
        logger.info(f"✅ Completed task: {task.title} ({task_id})")
        
        return task
    
    def fail_task(
        self,
        task_id: str,
        error: str,
        retry: bool = True
    ) -> Optional[Task]:
        """Mark task as failed"""
        if not self._current_task_list:
            raise ValueError("No task list loaded")
        
        task = self._get_task(task_id)
        if not task:
            return None
        
        task.retry_count += 1
        
        if retry and task.retry_count < task.max_retries:
            logger.warning(f"⚠️ Task {task_id} failed (retry {task.retry_count}/{task.max_retries}): {error}")
            task.error = error
            # Keep in_progress for retry
        else:
            task.status = TaskStatus.FAILED
            task.error = error
            logger.error(f"❌ Task {task_id} failed permanently: {error}")
        
        self.save(self._current_task_list)
        return task
    
    # ========================================
    # CRASH RECOVERY
    # ========================================
    
    def resume(self, task_list_id: Optional[str] = None) -> Dict[str, Any]:
        """
        CRASH RECOVERY: Resume from last state
        
        Returns:
            {
                "task_list": TaskList,
                "resume_task": Task or None,
                "checkpoint": TaskCheckpoint or None,
                "next_tasks": List[Task]
            }
        """
        # Find most recent task list if not specified
        if not task_list_id:
            task_lists = self.list_task_lists()
            if not task_lists:
                return {"error": "No task lists found"}
            task_list_id = task_lists[0]["id"]
        
        task_list = self.load(task_list_id)
        if not task_list:
            return {"error": f"Task list not found: {task_list_id}"}
        
        # Find task to resume
        resume_task = None
        checkpoint = None
        
        # First priority: last active task
        if task_list.last_active_task_id:
            resume_task = self._get_task(task_list.last_active_task_id)
            if resume_task and resume_task.status == TaskStatus.IN_PROGRESS:
                checkpoint = resume_task.checkpoint
        
        # Second priority: any in_progress task
        if not resume_task:
            for task in task_list.tasks:
                if task.status == TaskStatus.IN_PROGRESS:
                    resume_task = task
                    checkpoint = task.checkpoint
                    break
        
        # Find next available tasks
        next_tasks = self._get_ready_tasks()
        
        result = {
            "task_list": task_list,
            "resume_task": resume_task,
            "checkpoint": checkpoint,
            "next_tasks": next_tasks,
            "progress": task_list.progress_pct,
            "status_summary": task_list.status_summary
        }
        
        if resume_task and checkpoint:
            logger.info(
                f"🔄 RESUME: {resume_task.title} at {checkpoint.progress_pct}% "
                f"(item: {checkpoint.current_item})"
            )
        elif next_tasks:
            logger.info(f"▶️ READY: {len(next_tasks)} tasks available to start")
        else:
            logger.info(f"✅ COMPLETE: Task list {task_list.progress_pct}% done")
        
        return result
    
    def get_resume_prompt(self) -> str:
        """Generate a prompt for resuming work"""
        result = self.resume()
        
        if "error" in result:
            return f"No task list found. Create new with: manager.create_biddeed_pipeline('2026-01-28')"
        
        task_list = result["task_list"]
        resume_task = result.get("resume_task")
        checkpoint = result.get("checkpoint")
        next_tasks = result.get("next_tasks", [])
        
        lines = [
            "=" * 60,
            "📋 SINGLE SOURCE OF TRUTH - SESSION RESUME",
            "=" * 60,
            f"Task List: {task_list.name}",
            f"Progress: {task_list.progress_pct}%",
            f"Status: {result['status_summary']}",
            ""
        ]
        
        if resume_task:
            lines.extend([
                "🔄 RESUME TASK:",
                f"   ID: {resume_task.id}",
                f"   Title: {resume_task.title}",
                f"   Stage: {resume_task.stage}",
                f"   Agent: {resume_task.assigned_agent}",
            ])
            if checkpoint:
                lines.extend([
                    f"   Progress: {checkpoint.progress_pct}%",
                    f"   Current Item: {checkpoint.current_item}",
                    f"   Completed: {checkpoint.items_completed}/{checkpoint.items_total}",
                ])
                if checkpoint.context:
                    lines.append(f"   Context: {json.dumps(checkpoint.context, indent=6)}")
            lines.append("")
        
        if next_tasks:
            lines.append("▶️ READY TO START:")
            for task in next_tasks[:5]:
                lines.append(f"   - [{task.id}] {task.title} ({task.assigned_agent})")
            lines.append("")
        
        lines.extend([
            "=" * 60,
            "Commands: start_task(id), complete_task(id), update_checkpoint(id, pct)",
            "=" * 60,
        ])
        
        return "\n".join(lines)
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    def _get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        if not self._current_task_list:
            return None
        for task in self._current_task_list.tasks:
            if task.id == task_id:
                return task
        return None
    
    def _get_blocking_dependencies(self, task: Task) -> List[str]:
        """Get list of incomplete dependencies"""
        blocking = []
        for dep_id in task.depends_on:
            dep_task = self._get_task(dep_id)
            if dep_task and dep_task.status != TaskStatus.COMPLETED:
                blocking.append(dep_id)
        return blocking
    
    def _get_ready_tasks(self) -> List[Task]:
        """Get tasks that are ready to start (no blocking dependencies)"""
        if not self._current_task_list:
            return []
        
        ready = []
        for task in self._current_task_list.tasks:
            if task.status != TaskStatus.PENDING:
                continue
            if not self._get_blocking_dependencies(task):
                ready.append(task)
        
        return ready
    
    def _update_blocked_tasks(self) -> None:
        """Update blocked status for all tasks"""
        if not self._current_task_list:
            return
        
        for task in self._current_task_list.tasks:
            if task.status == TaskStatus.BLOCKED:
                if not self._get_blocking_dependencies(task):
                    task.status = TaskStatus.PENDING
                    logger.info(f"🔓 Unblocked task: {task.title}")
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return f"session-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    
    def _sync_to_supabase(self, task_list: TaskList) -> None:
        """Backup task list to Supabase (secondary storage)"""
        if not self.supabase:
            return
        
        # This is backup only - file system is SSOT
        self.supabase.table("ssot_task_lists").upsert({
            "id": task_list.id,
            "name": task_list.name,
            "data": task_list.model_dump(mode='json'),
            "progress_pct": task_list.progress_pct,
            "updated_at": datetime.utcnow().isoformat()
        }).execute()
    
    # ========================================
    # REPORTING
    # ========================================
    
    def get_status_report(self) -> str:
        """Generate human-readable status report"""
        if not self._current_task_list:
            return "No task list loaded"
        
        tl = self._current_task_list
        
        lines = [
            f"📋 {tl.name}",
            f"Progress: {'█' * (tl.progress_pct // 10)}{'░' * (10 - tl.progress_pct // 10)} {tl.progress_pct}%",
            "",
            "Tasks:"
        ]
        
        status_icons = {
            TaskStatus.PENDING: "⬜",
            TaskStatus.IN_PROGRESS: "🔵",
            TaskStatus.BLOCKED: "🟡",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.SKIPPED: "⏭️",
            TaskStatus.DEFERRED: "📅"
        }
        
        for task in tl.tasks:
            icon = status_icons.get(task.status, "❓")
            deps = f" (blocked by: {task.depends_on})" if task.status == TaskStatus.BLOCKED else ""
            checkpoint_info = ""
            if task.checkpoint and task.status == TaskStatus.IN_PROGRESS:
                checkpoint_info = f" [{task.checkpoint.progress_pct}%]"
            lines.append(f"  {icon} [{task.id}] {task.title}{checkpoint_info}{deps}")
        
        return "\n".join(lines)
