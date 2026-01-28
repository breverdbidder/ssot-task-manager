#!/usr/bin/env python3
"""
SINGLE SOURCE OF TRUTH (SSOT) - CLI Interface
==============================================
Command-line tool for managing persistent task lists.

Usage:
    ssot create auction-2026-01-28 --count 23
    ssot resume
    ssot status
    ssot start t01
    ssot checkpoint t01 --progress 50 --item "parcel_2612345"
    ssot complete t01
    ssot list

Author: BidDeed.AI / Everest Capital USA
"""

import argparse
import sys
import json
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.manager import TaskManager
from src.schema import TaskStatus


def main():
    parser = argparse.ArgumentParser(
        description="SSOT - Single Source of Truth Task Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ssot create 2026-01-28 --count 23    Create pipeline for auction date
  ssot resume                           Resume from last session
  ssot resume auction-2026-01-28        Resume specific task list
  ssot status                           Show current task list status
  ssot start t01                        Start task t01
  ssot checkpoint t01 -p 50 -i parcel_123   Update checkpoint
  ssot complete t01                     Mark task as completed
  ssot fail t01 --error "API timeout"   Mark task as failed
  ssot list                             List all task lists
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # CREATE command
    create_parser = subparsers.add_parser("create", help="Create new BidDeed pipeline")
    create_parser.add_argument("date", help="Auction date (YYYY-MM-DD)")
    create_parser.add_argument("-c", "--count", type=int, default=0, help="Property count")
    create_parser.add_argument("--dir", default=".claude/tasks", help="Tasks directory")
    
    # RESUME command
    resume_parser = subparsers.add_parser("resume", help="Resume from last session")
    resume_parser.add_argument("task_list_id", nargs="?", help="Specific task list ID")
    resume_parser.add_argument("--dir", default=".claude/tasks", help="Tasks directory")
    
    # STATUS command
    status_parser = subparsers.add_parser("status", help="Show current task list status")
    status_parser.add_argument("task_list_id", nargs="?", help="Specific task list ID")
    status_parser.add_argument("--dir", default=".claude/tasks", help="Tasks directory")
    status_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # START command
    start_parser = subparsers.add_parser("start", help="Start a task")
    start_parser.add_argument("task_id", help="Task ID to start")
    start_parser.add_argument("--list", dest="task_list_id", help="Task list ID")
    start_parser.add_argument("--dir", default=".claude/tasks", help="Tasks directory")
    
    # CHECKPOINT command
    checkpoint_parser = subparsers.add_parser("checkpoint", help="Update task checkpoint")
    checkpoint_parser.add_argument("task_id", help="Task ID")
    checkpoint_parser.add_argument("-p", "--progress", type=int, required=True, help="Progress %")
    checkpoint_parser.add_argument("-i", "--item", help="Current item being processed")
    checkpoint_parser.add_argument("--completed", type=int, default=0, help="Items completed")
    checkpoint_parser.add_argument("--total", type=int, default=0, help="Total items")
    checkpoint_parser.add_argument("--context", help="JSON context data")
    checkpoint_parser.add_argument("--list", dest="task_list_id", help="Task list ID")
    checkpoint_parser.add_argument("--dir", default=".claude/tasks", help="Tasks directory")
    
    # COMPLETE command
    complete_parser = subparsers.add_parser("complete", help="Mark task as completed")
    complete_parser.add_argument("task_id", help="Task ID to complete")
    complete_parser.add_argument("--output", help="JSON output data")
    complete_parser.add_argument("--list", dest="task_list_id", help="Task list ID")
    complete_parser.add_argument("--dir", default=".claude/tasks", help="Tasks directory")
    
    # FAIL command
    fail_parser = subparsers.add_parser("fail", help="Mark task as failed")
    fail_parser.add_argument("task_id", help="Task ID")
    fail_parser.add_argument("--error", required=True, help="Error message")
    fail_parser.add_argument("--no-retry", action="store_true", help="Don't allow retry")
    fail_parser.add_argument("--list", dest="task_list_id", help="Task list ID")
    fail_parser.add_argument("--dir", default=".claude/tasks", help="Tasks directory")
    
    # LIST command
    list_parser = subparsers.add_parser("list", help="List all task lists")
    list_parser.add_argument("--dir", default=".claude/tasks", help="Tasks directory")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize manager
    tasks_dir = getattr(args, "dir", ".claude/tasks")
    manager = TaskManager(tasks_dir=tasks_dir)
    
    # Execute command
    if args.command == "create":
        task_list = manager.create_biddeed_pipeline(
            auction_date=args.date,
            property_count=args.count
        )
        print(f"✅ Created: {task_list.id}")
        print(f"   Name: {task_list.name}")
        print(f"   Tasks: {len(task_list.tasks)}")
        print(f"   File: {tasks_dir}/{task_list.id}.json")
    
    elif args.command == "resume":
        result = manager.resume(args.task_list_id)
        if "error" in result:
            print(f"❌ {result['error']}")
            return 1
        print(manager.get_resume_prompt())
    
    elif args.command == "status":
        task_list_id = args.task_list_id
        if not task_list_id:
            # Get most recent
            task_lists = manager.list_task_lists()
            if not task_lists:
                print("No task lists found")
                return 1
            task_list_id = task_lists[0]["id"]
        
        task_list = manager.load(task_list_id)
        if not task_list:
            print(f"Task list not found: {task_list_id}")
            return 1
        
        if args.json:
            print(json.dumps(task_list.model_dump(mode='json'), indent=2, default=str))
        else:
            print(manager.get_status_report())
    
    elif args.command == "start":
        task_list_id = args.task_list_id
        if not task_list_id:
            task_lists = manager.list_task_lists()
            if task_lists:
                task_list_id = task_lists[0]["id"]
        
        if task_list_id:
            manager.load(task_list_id)
        
        task = manager.start_task(args.task_id)
        if task:
            if task.status == TaskStatus.BLOCKED:
                print(f"⛔ Task {task.id} is blocked by: {task.depends_on}")
            else:
                print(f"▶️ Started: {task.title}")
        else:
            print(f"❌ Task not found: {args.task_id}")
            return 1
    
    elif args.command == "checkpoint":
        task_list_id = args.task_list_id
        if not task_list_id:
            task_lists = manager.list_task_lists()
            if task_lists:
                task_list_id = task_lists[0]["id"]
        
        if task_list_id:
            manager.load(task_list_id)
        
        context = json.loads(args.context) if args.context else None
        manager.update_checkpoint(
            task_id=args.task_id,
            progress_pct=args.progress,
            current_item=args.item,
            items_completed=args.completed,
            items_total=args.total,
            context=context
        )
        print(f"💾 Checkpoint saved: {args.task_id} at {args.progress}%")
    
    elif args.command == "complete":
        task_list_id = args.task_list_id
        if not task_list_id:
            task_lists = manager.list_task_lists()
            if task_lists:
                task_list_id = task_lists[0]["id"]
        
        if task_list_id:
            manager.load(task_list_id)
        
        output = json.loads(args.output) if args.output else None
        task = manager.complete_task(args.task_id, output=output)
        if task:
            print(f"✅ Completed: {task.title}")
        else:
            print(f"❌ Task not found: {args.task_id}")
            return 1
    
    elif args.command == "fail":
        task_list_id = args.task_list_id
        if not task_list_id:
            task_lists = manager.list_task_lists()
            if task_lists:
                task_list_id = task_lists[0]["id"]
        
        if task_list_id:
            manager.load(task_list_id)
        
        task = manager.fail_task(
            args.task_id,
            error=args.error,
            retry=not args.no_retry
        )
        if task:
            if task.status == TaskStatus.FAILED:
                print(f"❌ Failed permanently: {task.title}")
            else:
                print(f"⚠️ Failed (retry {task.retry_count}/{task.max_retries}): {task.title}")
        else:
            print(f"❌ Task not found: {args.task_id}")
            return 1
    
    elif args.command == "list":
        task_lists = manager.list_task_lists()
        
        if args.json:
            print(json.dumps(task_lists, indent=2))
        else:
            if not task_lists:
                print("No task lists found")
                return 0
            
            print("📋 Task Lists:")
            print("-" * 60)
            for tl in task_lists:
                print(f"  [{tl['id']}] {tl['name']}")
                print(f"      Progress: {tl['progress']} | Status: {tl['status']}")
                print(f"      Updated: {tl['updated_at']}")
            print("-" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
