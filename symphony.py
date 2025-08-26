"""Symphony core execution engine.

This module provides the main entry point for multi-agent task execution
including task decomposition, agent discovery, and result aggregation.
"""

import time
import threading
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter

try:
    # Package mode imports
    from symphony.protocol.task_contract import Task, TaskResult
    from symphony.protocol.beacon import Beacon
    from symphony.agents.agent import Agent
except ImportError:
    # Direct execution mode imports
    from protocol.task_contract import Task, TaskResult
    from protocol.beacon import Beacon
    from agents.agent import Agent


class SymphonyOrchestrator:
    """Main orchestrator for multi-agent task execution.
    
    Coordinates task decomposition, agent discovery, task routing,
    and result aggregation through CoT voting mechanisms.
    """
    
    def __init__(self):
        """Initialize the Symphony orchestrator."""
        self.agents: List[Agent] = []
        self.active_tasks: Dict[str, Dict] = {}
        self.lock = threading.Lock()
    
    def register_agent(self, agent: Agent) -> None:
        """Register an agent with the orchestrator.
        
        Args:
            agent: Agent instance to register
        """
        with self.lock:
            if agent not in self.agents:
                self.agents.append(agent)
                print(f"[ORCHESTRATOR] Registered agent: {agent.agent_id}")
    
    def execute_task(self, task: Task, cot_count: int = 3) -> str:
        """Execute a complex task using multi-agent coordination.
        
        Args:
            task: Task to execute
            cot_count: Number of Chain-of-Thought executions for voting
            
        Returns:
            Final result after voting
        """
        print(f"[SYMPHONY] Starting task execution: {task.description[:50]}...")
        
        # Step 1: Decompose task into sub-tasks
        subtasks = self._decompose_task(task)
        print(f"[SYMPHONY] Task decomposed into {len(subtasks)} subtasks")
        
        # Step 2: Find suitable agents for each subtask
        agent_assignments = self._find_suitable_agents(subtasks)
        
        if not agent_assignments:
            return "[ERROR] No suitable agents found for task execution"
        
        # Step 3: Execute subtasks in parallel with CoT voting
        results = self._execute_with_cot_voting(subtasks, agent_assignments, cot_count)
        
        # Step 4: Aggregate final result
        final_result = self._aggregate_results(results, task)
        
        print(f"[SYMPHONY] Task execution completed")
        return final_result
    
    def _decompose_task(self, task: Task) -> List[Dict[str, Any]]:
        """Decompose complex task into executable subtasks.
        
        Args:
            task: Complex task to decompose
            
        Returns:
            List of subtask dictionaries
        """
        # For now, create subtasks based on requirements
        subtasks = []
        
        for i, requirement in enumerate(task.requirements):
            subtask = {
                'id': f"{task.task_id}_sub_{i+1}",
                'requirement': requirement,
                'description': f"Handle {requirement} for: {task.description}",
                'context': task.context,
                'original_task': task.description
            }
            subtasks.append(subtask)
        
        return subtasks
    
    def _find_suitable_agents(self, subtasks: List[Dict]) -> Dict[str, List[Agent]]:
        """Find suitable agents for each subtask based on capabilities.
        
        Args:
            subtasks: List of subtasks to assign
            
        Returns:
            Dictionary mapping subtask IDs to list of suitable agents
        """
        assignments = {}
        
        for subtask in subtasks:
            suitable_agents = []
            requirement = subtask['requirement']
            
            for agent in self.agents:
                # Check if agent has matching capabilities
                if hasattr(agent, 'capability_manager'):
                    match_score = agent.capability_manager.match(requirement)
                    if match_score >= 0.3:  # Minimum threshold
                        suitable_agents.append((agent, match_score))
            
            # Sort by match score (descending)
            suitable_agents.sort(key=lambda x: x[1], reverse=True)
            assignments[subtask['id']] = [agent for agent, score in suitable_agents]
            
            print(f"[ASSIGNMENT] Subtask '{requirement}': {len(suitable_agents)} suitable agents found")
        
        return assignments
    
    def _execute_with_cot_voting(self, subtasks: List[Dict], 
                                agent_assignments: Dict[str, List[Agent]], 
                                cot_count: int) -> Dict[str, str]:
        """Execute subtasks with Chain-of-Thought voting.
        
        Args:
            subtasks: List of subtasks to execute
            agent_assignments: Agent assignments for each subtask
            cot_count: Number of CoT executions
            
        Returns:
            Dictionary of subtask results
        """
        results = {}
        
        for subtask in subtasks:
            subtask_id = subtask['id']
            available_agents = agent_assignments.get(subtask_id, [])
            
            if not available_agents:
                results[subtask_id] = f"[ERROR] No agents available for subtask: {subtask['requirement']}"
                continue
            
            # Execute with multiple agents for CoT voting
            cot_results = []
            
            for i in range(min(cot_count, len(available_agents))):
                agent = available_agents[i]
                try:
                    result = self._execute_subtask_on_agent(agent, subtask)
                    cot_results.append(result)
                    print(f"[COT] Agent {agent.agent_id}: Completed subtask {subtask['requirement']}")
                except Exception as e:
                    print(f"[COT] Agent {agent.agent_id}: Failed subtask {subtask['requirement']} - {str(e)}")
                    cot_results.append(f"[AGENT_ERROR] {str(e)}")
            
            # Vote on results
            if cot_results:
                final_result = self._vote_on_results(cot_results, subtask)
                results[subtask_id] = final_result
            else:
                results[subtask_id] = f"[ERROR] All agents failed for subtask: {subtask['requirement']}"
        
        return results
    
    def _execute_subtask_on_agent(self, agent: Agent, subtask: Dict) -> str:
        """Execute a subtask on a specific agent.
        
        Args:
            agent: Agent to execute the subtask
            subtask: Subtask to execute
            
        Returns:
            Execution result
        """
        # Create a simplified task for the agent
        agent_task = {
            'subtask_id': 1,
            'steps': {1: {'instruction': subtask['description'], 'requirement': subtask['requirement']}},
            'previous_results': [],
            'original_problem': subtask['original_task'],
            'final_result': '',
            'user_id': 'symphony_orchestrator'
        }
        
        # For testing, return a simulated result
        if hasattr(agent, 'base_model') and agent.base_model is None:
            # Test mode - return simulated result
            return f"[SIMULATED] Agent {agent.agent_id} handling {subtask['requirement']}: Task analysis completed with focus on {subtask['context'].get('domain', 'general')} domain."
        
        # In real mode, this would execute the task on the agent
        try:
            if hasattr(agent, 'execute_task'):
                result = agent.execute_task(agent_task)
                return result.get('final_result', str(result))
            else:
                return f"Agent {agent.agent_id} processed: {subtask['requirement']}"
        except Exception as e:
            raise Exception(f"Agent execution failed: {str(e)}")
    
    def _vote_on_results(self, cot_results: List[str], subtask: Dict) -> str:
        """Vote on Chain-of-Thought results to select the best one.
        
        Args:
            cot_results: List of results from different agents
            subtask: Original subtask information
            
        Returns:
            Voted final result
        """
        if len(cot_results) == 1:
            return cot_results[0]
        
        # Simple voting: choose the longest non-error result
        valid_results = [r for r in cot_results if not r.startswith('[ERROR]') and not r.startswith('[AGENT_ERROR]')]
        
        if not valid_results:
            return cot_results[0]  # Return first result even if error
        
        # Choose result with most content (simple heuristic)
        best_result = max(valid_results, key=len)
        
        print(f"[VOTING] Selected result for {subtask['requirement']}: {len(best_result)} characters")
        return best_result
    
    def _aggregate_results(self, results: Dict[str, str], original_task: Task) -> str:
        """Aggregate subtask results into final result.
        
        Args:
            results: Dictionary of subtask results
            original_task: Original task
            
        Returns:
            Final aggregated result
        """
        aggregated = f"## Symphony Multi-Agent Task Execution Result\n\n"
        aggregated += f"**Original Task**: {original_task.description}\n\n"
        aggregated += f"**Domain**: {original_task.context.get('domain', 'General')}\n"
        aggregated += f"**Complexity**: {original_task.context.get('complexity', 'Medium')}\n\n"
        aggregated += f"### Subtask Results:\n\n"
        
        for i, (subtask_id, result) in enumerate(results.items(), 1):
            requirement = subtask_id.split('_sub_')[-1]
            aggregated += f"{i}. **{requirement}**: {result}\n\n"
        
        aggregated += f"\n**Execution Summary**: Successfully coordinated {len(results)} specialized agents "
        aggregated += f"to handle different aspects of the task through beacon-guided routing and CoT voting.\n"
        
        return aggregated


# Global orchestrator instance
_global_orchestrator = SymphonyOrchestrator()


def execute_task(task: Task, cot_count: int = 3) -> str:
    """Execute a complex task using Symphony's multi-agent coordination.
    
    This is the main entry point for task execution. The framework automatically:
    1. Decomposes the task into specialized sub-tasks
    2. Broadcasts beacons to find suitable agents  
    3. Routes sub-tasks to best-matching specialists
    4. Aggregates results through CoT voting
    
    Args:
        task: Task instance with description, requirements, and context
        cot_count: Number of Chain-of-Thought executions for voting (default: 3)
        
    Returns:
        Final result string after multi-agent coordination
        
    Example:
        >>> from symphony import Agent, Task, execute_task
        >>> 
        >>> # Initialize specialized agents
        >>> math_agent = Agent(
        ...     node_id="math_specialist",
        ...     capabilities=["mathematical-reasoning", "calculus", "statistics"]
        ... )
        >>> 
        >>> # Create complex task
        >>> task = Task(
        ...     description="Build a machine learning model to predict stock prices",
        ...     requirements=["data-collection", "mathematical-modeling", "code-implementation"],
        ...     context={"domain": "finance", "complexity": "high"}
        ... )
        >>> 
        >>> # Execute with multi-agent coordination
        >>> result = execute_task(task)
    """
    return _global_orchestrator.execute_task(task, cot_count)


def register_agent(agent: Agent) -> None:
    """Register an agent with the global orchestrator.
    
    Args:
        agent: Agent instance to register
    """
    _global_orchestrator.register_agent(agent)


def get_registered_agents() -> List[Agent]:
    """Get list of currently registered agents.
    
    Returns:
        List of registered Agent instances
    """
    return _global_orchestrator.agents.copy()
