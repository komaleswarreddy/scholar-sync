"""
Evaluation Scheduler

Scheduled evaluation jobs for continuous monitoring.
"""

import asyncio
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import time


@dataclass
class ScheduledEval:
    """Scheduled evaluation job."""
    name: str
    interval_seconds: int
    last_run: Optional[datetime]
    enabled: bool
    callback: Callable


class EvaluationScheduler:
    """
    Schedules and runs periodic evaluations.
    
    Runs evaluations on schedule to catch regressions early.
    """
    
    def __init__(self):
        """Initialize scheduler."""
        self.jobs: Dict[str, ScheduledEval] = {}
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    def register_eval(
        self,
        name: str,
        interval_seconds: int,
        callback: Callable,
        enabled: bool = True
    ):
        """
        Register an evaluation job.
        
        Args:
            name: Job name
            interval_seconds: Run interval in seconds
            callback: Async function to call
            enabled: Whether job is enabled
        """
        self.jobs[name] = ScheduledEval(
            name=name,
            interval_seconds=interval_seconds,
            last_run=None,
            enabled=enabled,
            callback=callback
        )
    
    async def start(self):
        """Start scheduler."""
        if self.running:
            return
        
        self.running = True
        self._task = asyncio.create_task(self._run_loop())
        print("[EVAL_SCHEDULER] Started evaluation scheduler")
    
    async def stop(self):
        """Stop scheduler."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("[EVAL_SCHEDULER] Stopped evaluation scheduler")
    
    async def _run_loop(self):
        """Main scheduler loop."""
        while self.running:
            try:
                current_time = datetime.utcnow()
                
                for job in self.jobs.values():
                    if not job.enabled:
                        continue
                    
                    # Check if it's time to run
                    should_run = False
                    if job.last_run is None:
                        # First run
                        should_run = True
                    else:
                        elapsed = (current_time - job.last_run).total_seconds()
                        if elapsed >= job.interval_seconds:
                            should_run = True
                    
                    if should_run:
                        try:
                            print(f"[EVAL_SCHEDULER] Running evaluation: {job.name}")
                            if asyncio.iscoroutinefunction(job.callback):
                                await job.callback()
                            else:
                                job.callback()
                            job.last_run = current_time
                        except Exception as e:
                            print(f"[ERROR] Evaluation job {job.name} failed: {e}")
                            import traceback
                            traceback.print_exc()
                
                # Sleep for 60 seconds before next check
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ERROR] Scheduler loop error: {e}")
                await asyncio.sleep(60)
    
    def run_now(self, name: str):
        """Run a specific evaluation job now."""
        if name in self.jobs:
            job = self.jobs[name]
            if asyncio.iscoroutinefunction(job.callback):
                asyncio.create_task(job.callback())
            else:
                job.callback()
            job.last_run = datetime.utcnow()
