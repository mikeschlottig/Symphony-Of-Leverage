"""Agent implementation for distributed computation in Symphony Network.

This module implements the Agent class which handles distributed computation
tasks in the Symphony Network, including task execution, assignment, and
communication with other network nodes.
"""

from typing import Dict, List, Tuple, Optional, Any

# Try to import dependencies, fallback gracefully if not available
try:
    from models.base_loader import BaseModel
except ImportError:
    print("[WARNING] BaseModel not available, using mock implementation")
    BaseModel = None

try:
    from protocol.beacon import Beacon
    from protocol.response import BeaconResponse
except ImportError:
    print("[WARNING] Protocol modules not fully available")
    Beacon = None
    BeaconResponse = None

try:
    from core.capability import CapabilityManager
    from core.memory import LocalMemory
except ImportError:
    print("[WARNING] Core modules not available")
    # Mock implementations
    class CapabilityManager:
        def __init__(self, capabilities):
            self.capabilities = capabilities
        def match(self, requirement):
            return 0.5 if requirement in ' '.join(self.capabilities) else 0.1
    
    class LocalMemory:
        def __init__(self):
            pass

try:
    from protocol.task_contract import TaskResult, Task
except ImportError:
    print("[WARNING] Task contract not available")
    TaskResult = None
    Task = None

try:
    from infra.ISEP import ISEPClient
    from infra.network_adapter import NetworkAdapter
except ImportError:
    print("[WARNING] Network infrastructure not available")
    ISEPClient = None
    NetworkAdapter = None


class Agent:
    """Agent for handling distributed computation tasks in Symphony Network.
    
    This class represents a computational agent that can execute tasks,
    coordinate with other agents, and manage its capabilities within
    the distributed Symphony Network.
    
    Attributes:
        agent_id (str): Unique identifier for this agent
        gpu_id (int): GPU device ID for computation
        system_prompt (str): System prompt for the agent
        base_model (Optional[BaseModel]): Base model for task execution
        capabilities (List[str]): List of agent capabilities
        memory (LocalMemory): Local memory management
        capability_manager (CapabilityManager): Capability matching manager
        network (NetworkAdapter): Network communication adapter
        isep_client (ISEPClient): ISEP protocol client
    """
    
    def __init__(self, 
                 # New simplified API (README style)
                 node_id: str = None,
                 capabilities: List[str] = None,
                 system_prompt: str = None,
                 base_model: str = None,
                 gpu_id: int = 0,
                 # Legacy config API
                 config: Dict[str, Any] = None) -> None:
        """Initialize Agent with simplified parameters or legacy config.
        
        Can be used in two ways:
        
        1. New simplified API (preferred):
           Agent(node_id="agent_001", capabilities=["math", "reasoning"])
           
        2. Legacy config API:
           Agent(config={"node_id": "agent_001", "capabilities": [...], ...})
        
        Args:
            node_id: Unique agent identifier (new API)
            capabilities: List of agent capabilities (new API)
            system_prompt: System prompt for the agent (new API)
            base_model: Base model type or 'test' for testing (new API)
            gpu_id: GPU device ID (new API, default: 0)
            config: Legacy configuration dictionary
        
        Raises:
            KeyError: If required configuration keys are missing
            ValueError: If configuration values are invalid
        """
        # Determine which API is being used
        if config is not None:
            # Legacy config API
            self._init_from_config(config)
        else:
            # New simplified API
            self._init_from_params(node_id, capabilities, system_prompt, 
                                 base_model, gpu_id)
    
    def _init_from_config(self, config: Dict[str, Any]) -> None:
        """Initialize from legacy config dictionary."""
        self.agent_id = config["node_id"]
        self.gpu_id = config.get("gpu_id", 0)
        self.system_prompt = config.get("sys_prompt", "You are a helpful AI assistant.")
        
        # Initialize base model (skip if in test mode or not available)
        if BaseModel is None or config.get("base_model") == "test":
            self.base_model = None
        else:
            try:
                self.base_model = BaseModel(
                    config["base_model"], 
                    config["sys_prompt"], 
                    device=f"cuda:{self.gpu_id}"
                )
            except:
                print(f"[WARNING] Could not initialize base model, using test mode")
                self.base_model = None
        
        self.capabilities = config.get("capabilities", [])
        self.memory = LocalMemory()
        self.capability_manager = CapabilityManager(self.capabilities)
        
        # Initialize network components if neighbors are provided and available
        if "neighbours" in config and NetworkAdapter is not None and ISEPClient is not None:
            self.network = NetworkAdapter(self.agent_id, config)
            self.isep_client = ISEPClient(self.agent_id, self.network)
            self._initialize_neighbors(config["neighbours"])
        else:
            self.network = None
            self.isep_client = None
    
    def _init_from_params(self, node_id: str, capabilities: List[str], 
                         system_prompt: str, base_model: str, gpu_id: int) -> None:
        """Initialize from simplified parameters."""
        if node_id is None:
            raise ValueError("node_id is required")
        
        self.agent_id = node_id
        self.gpu_id = gpu_id
        self.system_prompt = system_prompt or "You are a helpful AI assistant specialized in complex reasoning tasks."
        self.capabilities = capabilities or []
        
        # For simplified API, default to test mode (no actual model loading)
        if base_model and base_model != "test" and BaseModel is not None:
            try:
                self.base_model = BaseModel(
                    base_model, 
                    self.system_prompt, 
                    device=f"cuda:{self.gpu_id}"
                )
            except:
                print(f"[WARNING] Could not initialize base model, using test mode")
                self.base_model = None
        else:
            self.base_model = None
        
        self.memory = LocalMemory()
        self.capability_manager = CapabilityManager(self.capabilities)
        
        # For simplified API, initialize minimal network (local only)
        self.network = None
        self.isep_client = None
        
        print(f"[AGENT] Initialized agent {self.agent_id} with capabilities: {self.capabilities}")
        
        # Auto-register with global orchestrator if available
        try:
            import symphony
            symphony.register_agent(self)
        except (ImportError, AttributeError):
            # symphony module not available or not imported yet
            pass
        
    def _initialize_neighbors(self, neighbors: List[Tuple[str, str, str]]) -> None:
        """Initialize neighbor nodes in the network.
        
        Args:
            neighbors: List of tuples containing (node_id, address, port)
        """
        for neighbor in neighbors:
            self.network.add_neighbor(
                neighbor[0], 
                neighbor[1], 
                int(neighbor[2])
            )
        
    def execute_task(self, task: Task) -> Task:
        """Execute a task or subtask.
        
        This method handles both task decomposition (when subtask_id is 0)
        and subtask execution (for subsequent subtasks).
        
        Args:
            task (Task): Task object to execute
            
        Returns:
            Task: Updated task object with execution results
            
        Raises:
            ValueError: If task format is invalid
            RuntimeError: If task execution fails
        """
        if task["subtask_id"] == 0:
            return self._decompose_task(task)
        else:
            return self._execute_subtask(task)
    
    def _decompose_task(self, task: Task) -> Task:
        """Decompose a task into subtasks.
        
        Args:
            task (Task): Original task to decompose
            
        Returns:
            Task: Task with decomposed subtasks
        """
        user_input = task["original_problem"]
        
        # Extract task components using base model
        task_background, task_question, success = self.base_model.extract_task(
            user_input
        )
        
        if success:
            task["previous_results"].append(task_background)
            
            # Generate task DAG (Directed Acyclic Graph)
            steps, dag_success = self.base_model.generate_task_dag(
                task_background, 
                task_question, 
                user_input, 
                "math"
            )
            
            if dag_success:
                task["steps"] = steps
                print(f"Generated task steps: {task['steps']}")
        
        task["subtask_id"] += 1
        return Task.from_dict(task)
    
    def _execute_subtask(self, task: Task) -> Task:
        """Execute a specific subtask.
        
        Args:
            task (Task): Task containing subtask to execute
            
        Returns:
            Task: Task with subtask execution result
        """
        current_subtask_id = str(task["subtask_id"])
        instruction = task["steps"][current_subtask_id][0]
        previous_results = task["previous_results"]
        
        # Combine previous results as context
        previous_context = " ".join(previous_results)
        
        # Create comprehensive task description
        task_description = self._build_task_description(
            instruction, 
            previous_context
        )
        
        # Generate result using base model
        result = self.base_model.generate(task_description)
        
        # Store execution result
        task["previous_results"].append(
            f"{instruction} Answer: {result}"
        )
        
        # Check if this is the final subtask
        if task["subtask_id"] == len(task["steps"]):
            task["final_result"] = result
            
        task["subtask_id"] += 1
        return Task.from_dict(task)
    
    def _build_task_description(self, instruction: str, context: str) -> str:
        """Build a comprehensive task description for execution.
        
        Args:
            instruction (str): Current subtask instruction
            context (str): Previous execution context
            
        Returns:
            str: Formatted task description
        """
        return (
            f"{self.system_prompt}\n"
            f"Background information include: \"{context}\". "
            f"Based on the background information, solve the sub-task: \"{instruction}\". "
            f"Provide the final answer formatted as $\\boxed{{<Answer>}}$. "
            f"Do not provide additional explanations or code. Output: "
        )
    
    def assign_task(self, task: Task) -> None:
        """Assign task to suitable executor nodes.
        
        This method broadcasts a beacon to find suitable executors
        and delegates the task to the best matches.
        
        Args:
            task (Task): Task to assign to executors
        """
        # Create beacon for task requirement discovery
        beacon = Beacon(
            sender=self.agent_id, 
            task_id=str(task.subtask_id), 
            requirement=task.steps[str(task.subtask_id)][1], 
            ttl=2
        )
        
        # Broadcast beacon and collect responses
        candidates = self.isep_client.broadcast_and_collect(beacon)
        best_matches = self._select_best_executors(candidates, 1)
        
        print(f"Selected executors: {best_matches}")
        
        # Delegate task to selected executors
        for executor_id, score in best_matches:
            self.isep_client.delegate_task(executor_id, task)
    
    def _select_best_executors(
        self, 
        candidates: List[Tuple[str, float]], 
        num_executors: int
    ) -> List[Tuple[str, float]]:
        """Select best executor nodes from candidates.
        
        This method sorts candidates by score and prioritizes self-execution
        when scores are equal.
        
        Args:
            candidates (List[Tuple[str, float]]): List of (node_id, score) tuples
            num_executors (int): Number of executors to select
            
        Returns:
            List[Tuple[str, float]]: Selected executor candidates
        """
        # Sort candidates by score in descending order
        sorted_candidates = sorted(
            candidates, 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Prioritize self if score equals the best score
        self._prioritize_self_execution(sorted_candidates)
        
        return sorted_candidates[:num_executors]
    
    def _prioritize_self_execution(
        self, 
        candidates: List[Tuple[str, float]]
    ) -> None:
        """Prioritize self-execution when scores are equal.
        
        Args:
            candidates (List[Tuple[str, float]]): Sorted candidate list to modify
        """
        if not candidates:
            return
            
        best_score = candidates[0][1]
        
        for i, (candidate_id, score) in enumerate(candidates):
            if candidate_id == self.agent_id and score == best_score:
                # Move self to first position
                candidates[i] = candidates[0]
                candidates[0] = (candidate_id, score)
                break
    
    def handle_beacon(
        self, 
        sender_id: str, 
        beacon: Beacon
    ) -> None:
        """Handle incoming beacon requests from other agents.
        
        This method calculates the agent's capability score for the
        requested task and sends a response back to the sender.
        
        Args:
            sender_id (str): ID of the beacon sender
            beacon (Beacon): Received beacon message containing task requirements
        """
        # Calculate capability match score
        match_score = self.capability_manager.match(
            beacon["requirement"]
        )
        
        # Create and send beacon response
        response = BeaconResponse(
            responder_id=self.agent_id,
            task_id=beacon["task_id"], 
            match_score=match_score
        )
        
        self.isep_client.send_response(sender_id, "beacon_response", response)
