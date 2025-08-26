"""Inter-node Service Exchange Protocol (ISEP) Client

ISEP client implementation for the Symphony distributed computing framework.
Provides standardized communication protocols for task delegation, result collection,
and service discovery between Symphony nodes.
"""

from typing import Dict, List, Optional
import time
from queue import Queue
from protocol.beacon import Beacon
from protocol.response import BeaconResponse
from protocol.task_contract import TaskResult, Task
from infra.network_adapter import NetworkAdapter


class ISEPClient:
    """Inter-node Service Exchange Protocol (ISEP) client implementation.
    
    Provides a simplified ISEP protocol client adapted for TaskRequester calling patterns.
    Handles service discovery through beacon broadcasting, task delegation, and result
    collection in distributed computing environments.
    
    Attributes:
        node_id (str): Unique identifier for this ISEP client node
        network (NetworkAdapter): Network adapter for message transmission
        response_timeout (int): Timeout for collecting beacon responses in seconds
        pending_tasks (Dict[str, List[BeaconResponse]]): Active tasks awaiting responses
        beacon_queue (Queue): Queue for received Beacon messages
        subtask_queue (Queue): Queue for received subtask assignments
        task_result_queue (Queue): Queue for received task execution results
        task_allocation (Dict): Current task allocation mappings
        requester_id (str): ID of the current task requester
    """
    
    def __init__(self, node_id: str, network_adapter: NetworkAdapter, response_timeout: int = 1):
        """Initialize ISEP client with network adapter and configuration.
        
        Args:
            node_id (str): Unique node identifier
            network_adapter (NetworkAdapter): Network adapter instance for communication
            response_timeout (int, optional): Response collection timeout in seconds. Defaults to 1.
        """
        self.node_id = node_id
        self.network = network_adapter
        self.response_timeout = response_timeout
        self.pending_tasks: Dict[str, List[BeaconResponse]] = {}  # task_id -> responses
        self.beacon_queue = Queue()  # Queue for storing received Beacon messages
        self.subtask_queue = Queue()
        self.task_result_queue = Queue()
        self.task_allocation = {}
        self.requester_id = ""
        
        # Register message handlers with network adapter
        self.network.register_handler("beacon", self._handle_beacon)
        self.network.register_handler("beacon_response", self._handle_beacon_response)
        self.network.register_handler("task", self._handle_task)
        self.network.register_handler("task_result", self._handle_task_result)
    
    def broadcast_and_collect(self, beacon: Beacon) -> List[BeaconResponse]:
        """Broadcast Beacon message and collect responses from available nodes.
        
        Initiates service discovery by broadcasting a beacon containing task requirements
        and capabilities needed. Collects responses from nodes that can handle the task.
        
        Args:
            beacon (Beacon): Beacon message containing task specifications
            
        Returns:
            List[BeaconResponse]: List of tuples containing (node_id, capability_score)
                representing available compute providers and their capability scores
        """
        self.pending_tasks[beacon.task_id] = []
        
        # Broadcast Beacon message to all known nodes
        self.network.broadcast("beacon", beacon)
        
        # Note: In production, might need more sophisticated asynchronous processing
        # Timer(self.response_timeout, self._timeout_collect, args=[beacon.task_id]).start()

        candidates = []  # IDs and capability scores of various compute providers

        # Wait for responses within timeout period
        time.sleep(self.response_timeout)
        responses = self.pending_tasks[beacon.task_id]
        for response in responses:
            candidates.append((response["responder_id"], response["match_score"]))
                    
        # Return collected responses (simplified implementation)
        return candidates
    
    def send_response(self, target_id, msg_type, response):
        """Send response message to target node.
        
        Args:
            target_id (str): Target node identifier
            msg_type (str): Type of response message
            response: Response data to send
        """
        self.network.send(target_id, msg_type, response)
    
    def delegate_task(self, executor_id: str, task: Task) -> str:
        """Delegate subtask to executor node.
        
        Assigns a specific task to an executor node that has the required capabilities.
        
        Args:
            executor_id (str): Identifier of the executor node
            task (Task): Task object containing execution specifications
            
        Returns:
            str: Task delegation result status
        """
        self.network.send(executor_id, "task", task)
    
    def submit_result(self, target_id, result, previous_results):
        """Submit task execution result to requesting node.
        
        Args:
            target_id (str): Target node identifier (usually the task requester)
            result: Task execution result data
            previous_results: Previous task execution results for context
        """
        # Create task result object
        task_result = TaskResult(
            target_id=target_id,
            executer_id=self.node_id,
            result=result,
            previous_results=previous_results
        )
        
        # Send result to target node
        self.network.send(target_id, "task_result", task_result)
    
    def _handle_beacon(self, sender_id: str, beacon: Beacon):
        """Handle received Beacon message for service discovery.
        
        Args:
            sender_id (str): Node ID of the beacon sender
            beacon (Beacon): Received beacon message containing task requirements
        """
        # Put received Beacon message into processing queue
        self.beacon_queue.put((sender_id, "beacon", beacon))
    
    def _handle_beacon_response(self, sender_id: str, response: BeaconResponse):
        """Handle received Beacon response from potential service providers.
        
        Args:
            sender_id (str): Node ID of the response sender
            response (BeaconResponse): Response containing capability information
        """
        if response["task_id"] in self.pending_tasks:
            self.pending_tasks[response["task_id"]].append(response)

    def _handle_task(self, sender_id: str, task: Task):
        """Handle received Task assignment for execution.
        
        Args:
            sender_id (str): Node ID of the task sender
            task (Task): Task object containing execution specifications
        """
        # Put received task message into processing queue
        self.subtask_queue.put((sender_id, "task", task))
    
    def _handle_task_result(self, sender_id: str, result: TaskResult):
        """Handle received task execution result.
        
        Args:
            sender_id (str): Node ID of the result sender
            result (TaskResult): Task execution result containing output data
        """
        # Add callback mechanism to notify TaskRequester if needed
        print(f"Received task result from {sender_id}: {result}")
        self.task_result_queue.put((sender_id, "task_result", result))
    
    def _timeout_collect(self, task_id: str):
        """Handle timeout for response collection.
        
        Args:
            task_id (str): Task identifier for which collection timed out
        """
        if task_id in self.pending_tasks:
            # Trigger callback to notify TaskRequester that response collection is complete
            print(f"Response collection for task {task_id} completed")
            # self.pending_tasks.pop(task_id)  # Should be deleted after TaskRequester reads

    def receive_beacon(self, timeout=None):
        """Retrieve received Beacon message from queue.
        
        Args:
            timeout: Timeout for queue get operation in seconds
            
        Returns:
            tuple: (sender_id, msg_type, beacon) or (None, None, None) if timeout
        """
        try:
            return self.beacon_queue.get(timeout=timeout)
        except Exception:
            return None, None, None

    def receive_task(self, timeout=None):
        """Retrieve received task message from queue.
        
        Args:
            timeout: Timeout for queue get operation in seconds
            
        Returns:
            tuple: (sender_id, msg_type, task) or (None, None, None) if timeout
        """
        try:
            return self.subtask_queue.get(timeout=timeout)
        except Exception:
            return None, None, None
        
    def receive_result(self, timeout=None):
        """Retrieve received result message from queue.
        
        Args:
            timeout: Timeout for queue get operation in seconds
            
        Returns:
            tuple: (sender_id, msg_type, result) or (None, None, None) if timeout
        """
        try:
            return self.task_result_queue.get(timeout=timeout)
        except Exception:
            return None, None, None
