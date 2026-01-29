import threading
import time
import queue
import logging
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Task:
    id: str
    function: Callable
    args: tuple
    kwargs: dict
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: float = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()

class FrameQueue:
    def __init__(self, max_workers=2):
        self.task_queue = queue.Queue()
        self.result_store = {}
        self.workers = []
        self.max_workers = max_workers
        self.is_running = False
        self.worker_thread = None
        
    def start(self):
        """Start the queue workers"""
        if self.is_running:
            logger.warning("FrameQueue is already running")
            return
            
        self.is_running = True
        self.workers = []
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker, name=f"FrameWorker-{i}")
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"Started FrameQueue with {self.max_workers} workers")
        
    def stop(self):
        """Stop the queue workers"""
        self.is_running = False
        
        # Add sentinel values to stop workers
        for _ in range(self.max_workers):
            self.task_queue.put(None)
            
        # Wait for workers to finish
        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=5)
                
        self.workers = []
        logger.info("Stopped FrameQueue")
        
    def add_task(self, task_id: str, function: Callable, *args, **kwargs) -> str:
        """Add a task to the queue"""
        task = Task(id=task_id, function=function, args=args, kwargs=kwargs)
        self.task_queue.put(task)
        self.result_store[task_id] = task
        logger.debug(f"Added task {task_id} to queue")
        return task_id
        
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a task"""
        task = self.result_store.get(task_id)
        if not task:
            return None
            
        return {
            'id': task.id,
            'status': task.status.value,
            'result': task.result,
            'error': task.error,
            'created_at': task.created_at,
            'started_at': task.started_at,
            'completed_at': task.completed_at,
            'duration': (task.completed_at or time.time()) - (task.started_at or task.created_at)
        }
        
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        completed_tasks = [t for t in self.result_store.values() if t.status == TaskStatus.COMPLETED]
        failed_tasks = [t for t in self.result_store.values() if t.status == TaskStatus.FAILED]
        pending_tasks = [t for t in self.result_store.values() if t.status == TaskStatus.PENDING]
        running_tasks = [t for t in self.result_store.values() if t.status == TaskStatus.RUNNING]
        
        return {
            'queue_size': self.task_queue.qsize(),
            'total_tasks': len(self.result_store),
            'completed_tasks': len(completed_tasks),
            'failed_tasks': len(failed_tasks),
            'pending_tasks': len(pending_tasks),
            'running_tasks': len(running_tasks),
            'active_workers': len([w for w in self.workers if w.is_alive()])
        }
        
    def _worker(self):
        """Worker thread to process tasks"""
        while self.is_running:
            try:
                task = self.task_queue.get(timeout=1)
                if task is None:  # Sentinel value to stop worker
                    break
                    
                task.status = TaskStatus.RUNNING
                task.started_at = time.time()
                
                try:
                    result = task.function(*task.args, **task.kwargs)
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    logger.debug(f"Task {task.id} completed successfully")
                    
                except Exception as e:
                    task.error = str(e)
                    task.status = TaskStatus.FAILED
                    logger.error(f"Task {task.id} failed: {str(e)}")
                    
                finally:
                    task.completed_at = time.time()
                    self.task_queue.task_done()
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker error: {str(e)}")

# Global queue instance
frame_queue = FrameQueue(max_workers=2)

def init_frame_queue():
    """Initialize the global frame queue"""
    frame_queue.start()
    
def shutdown_frame_queue():
    """Shutdown the global frame queue"""
    frame_queue.stop()

def add_frame_processing_task(task_id: str, function: Callable, *args, **kwargs) -> str:
    """Add a frame processing task to the queue"""
    return frame_queue.add_task(task_id, function, *args, **kwargs)

def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get the status of a frame processing task"""
    return frame_queue.get_task_status(task_id)

def get_queue_stats() -> Dict[str, Any]:
    """Get frame queue statistics"""
    return frame_queue.get_queue_stats()