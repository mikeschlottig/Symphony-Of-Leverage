# protocol/task_contract.py
"""Task contract and result definitions for distributed task execution.

This module provides the Task and TaskResult classes for managing
distributed task execution contracts and results in the symphony network.
"""

import uuid
import time
from typing import Dict, Any, List

__all__ = ['Task', 'TaskResult']


class TaskResult:
    """Task execution result container.
    
    Encapsulates the result of a task execution, including metadata
    about the executing and target nodes.
    
    Attributes:
        target_id (str): Target node identifier
        executer_id (str): Executing node identifier
        result (Any): Task execution result data
        previous_results (Any): Previous task results for context
    """
    
    def __init__(
        self, 
        target_id: str, 
        executer_id: str, 
        result: Any, 
        previous_results: Any
    ) -> None:
        """Initialize TaskResult.
        
        Args:
            target_id: Target node identifier
            executer_id: Executing node identifier
            result: Task execution result
            previous_results: Previous task results
        """
        self.target_id = target_id
        self.executer_id = executer_id
        self.result = result
        self.previous_results = previous_results

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format for serialization.
        
        Returns:
            Dictionary representation of the task result
        """
        return {
            "target_id": self.target_id,
            "executer_id": self.executer_id,
            "result": self.result,
            "previous_results": self.previous_results
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TaskResult':
        """Create TaskResult instance from dictionary data.
        
        Args:
            data: Dictionary containing result data
            
        Returns:
            TaskResult instance created from the dictionary
        """
        return TaskResult(
            target_id=data["target_id"],
            executer_id=data["executer_id"],
            result=data["result"],
            previous_results=data["previous_results"]
        )

    def __repr__(self) -> str:
        """Return string representation of the task result."""
        return f"<Result from {self.executer_id} to {self.target_id}>"


class Task:
    """Task contract for distributed computation.
    
    Represents a computational task that can be distributed across
    the symphony network. Supports both the new high-level API
    (description, requirements, context) and the legacy low-level API.
    
    New API Attributes:
        task_id (str): Unique task identifier
        description (str): High-level task description
        requirements (List[str]): List of capability requirements
        context (Dict[str, Any]): Task context and metadata
        
    Legacy API Attributes:
        subtask_id (int): Current subtask sequence number
        steps (Dict): Dictionary containing instruction and requirement for each step
        previous_results (List): Description and results of previous tasks
        original_problem (str): Original text input by user
        final_result (str): Final result placeholder
        user_id (str): User identifier
    """
    
    def __init__(
        self, 
        # New high-level API (README style)
        description: str = None,
        requirements: List[str] = None,
        context: Dict[str, Any] = None,
        task_id: str = None,
        # Legacy low-level API parameters
        subtask_id: int = None, 
        steps: Dict[str, Any] = None, 
        previous_results: List[Any] = None, 
        original_problem: str = None, 
        final_result: str = None, 
        user_id: str = None
    ) -> None:
        """Initialize Task instance.
        
        Can be used in two ways:
        
        1. New high-level API (preferred):
           Task(description="...", requirements=[...], context={...})
           
        2. Legacy low-level API:
           Task(subtask_id=0, steps={}, previous_results=[], ...)
        
        Args:
            description: High-level task description (new API)
            requirements: List of capability requirements (new API)
            context: Task context and metadata (new API)
            task_id: Unique task identifier (new API)
            subtask_id: Current subtask sequence number (legacy)
            steps: Dictionary containing instruction and requirement for each step (legacy)
            previous_results: Description and results of previous tasks (legacy)
            original_problem: Original text input by user (legacy)
            final_result: Final result (legacy)
            user_id: User identifier (legacy)
        """
        # Determine which API is being used
        if description is not None or requirements is not None:
            # New high-level API
            self.task_id = task_id or str(uuid.uuid4())
            self.description = description or ""
            self.requirements = requirements or []
            self.context = context or {}
            
            # Set legacy fields for backward compatibility
            self.subtask_id = subtask_id or 0
            self.steps = steps or {}
            self.previous_results = previous_results or []
            self.original_problem = original_problem or description or ""
            self.final_result = final_result or ""
            self.user_id = user_id or "symphony_user"
            
            # Flag to indicate which API was used
            self._api_mode = "high_level"
        else:
            # Legacy low-level API
            self.subtask_id = subtask_id or 0
            self.steps = steps or {}
            self.previous_results = previous_results or []
            self.original_problem = original_problem or ""
            self.final_result = final_result or ""
            self.user_id = user_id or "symphony_user"
            
            # Set new API fields from legacy data
            self.task_id = str(uuid.uuid4())
            self.description = original_problem or ""
            self.requirements = list(steps.keys()) if isinstance(steps, dict) else []
            self.context = {"mode": "legacy"}
            
            # Flag to indicate which API was used
            self._api_mode = "legacy"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Task object to dictionary format for JSON serialization.
        
        Returns:
            Dictionary representation of the task
        """
        base_dict = {
            "subtask_id": self.subtask_id,
            "steps": self.steps,
            "previous_results": self.previous_results,
            "original_problem": self.original_problem,
            "final_result": self.final_result,
            "user_id": self.user_id
        }
        
        # Add new API fields if available
        if hasattr(self, 'task_id'):
            base_dict.update({
                "task_id": self.task_id,
                "description": self.description,
                "requirements": self.requirements,
                "context": self.context,
                "api_mode": getattr(self, '_api_mode', 'legacy')
            })
        
        return base_dict
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Task':
        """Create Task instance from dictionary data.
        
        Args:
            data: Dictionary containing task data
            
        Returns:
            Task instance created from the dictionary
        """
        # Check if new API fields are present
        if 'description' in data or 'requirements' in data:
            return Task(
                description=data.get('description'),
                requirements=data.get('requirements', []),
                context=data.get('context', {}),
                task_id=data.get('task_id'),
                subtask_id=data.get('subtask_id'),
                steps=data.get('steps'),
                previous_results=data.get('previous_results'),
                original_problem=data.get('original_problem'),
                final_result=data.get('final_result'),
                user_id=data.get('user_id')
            )
        else:
            # Legacy mode
            return Task(
                subtask_id=data.get("subtask_id", 0),
                steps=data.get("steps", {}),
                previous_results=data.get("previous_results", []),
                original_problem=data.get("original_problem", ""),
                final_result=data.get("final_result", ""),
                user_id=data.get("user_id", "symphony_user")
            )
    
    def __repr__(self) -> str:
        """Return string representation of the task."""
        if hasattr(self, '_api_mode') and self._api_mode == 'high_level':
            return f"<Task '{self.description[:30]}...' requirements={len(self.requirements)}>"
        else:
            return f"<Task subtask_id={self.subtask_id} user_id='{self.user_id}'>"
    
    def __getitem__(self, key):
        """Dictionary-style access for backward compatibility."""
        return getattr(self, key)
    
    def get(self, key, default=None):
        """Dictionary-style get method for backward compatibility."""
        return getattr(self, key, default)
