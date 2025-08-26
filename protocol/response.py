# protocol/response.py
"""Beacon response handling for capability matching in symphony network.

This module provides the BeaconResponse class for nodes to respond to
Beacon messages when they can fulfill the requested capabilities.
"""

import uuid
import time
from typing import Dict


class BeaconResponse:
    """Response to a Beacon message indicating capability match.
    
    When a node receives a Beacon and determines it can fulfill the
    requested capability, it creates a BeaconResponse to communicate
    its availability and cost estimate.
    
    Attributes:
        response_id (str): Unique identifier for this response
        responder_id (str): ID of the responding node
        task_id (str): Task identifier from the original beacon
        match_score (float): Capability matching score (0.0 to 1.0)
        estimate_cost (float): Estimated cost of executing the task
        timestamp (int): Unix timestamp when response was created
    """
    
    def __init__(
        self, 
        responder_id: str, 
        task_id: str, 
        match_score: float = 1.0, 
        estimate_cost: float = 1.0
    ) -> None:
        """Initialize BeaconResponse.
        
        Args:
            responder_id: Current node ID
            task_id: Task identifier from the beacon
            match_score: Matching score with task requirements (0.0 to 1.0)
            estimate_cost: Estimated cost of executing the task
        """
        self.response_id = str(uuid.uuid4())
        self.responder_id = responder_id
        self.task_id = task_id
        self.match_score = round(max(0.0, min(1.0, match_score)), 3)
        self.estimate_cost = round(max(0.0, estimate_cost), 3)
        self.timestamp = int(time.time())

    def to_dict(self) -> Dict[str, any]:
        """Convert response to dictionary format for serialization.
        
        Returns:
            Dictionary representation of the beacon response
        """
        return {
            "response_id": self.response_id,
            "responder_id": self.responder_id,
            "task_id": self.task_id,
            "match_score": self.match_score,
            "estimate_cost": self.estimate_cost,
            "timestamp": self.timestamp
        }

    @staticmethod
    def from_dict(data: Dict[str, any]) -> 'BeaconResponse':
        """Create BeaconResponse instance from dictionary data.
        
        Args:
            data: Dictionary containing response data
            
        Returns:
            BeaconResponse instance created from the dictionary
        """
        resp = BeaconResponse(
            responder_id=data.get("responder_id", "unknown"),
            task_id=data.get("task_id", ""),
            match_score=data.get("match_score", 1.0),
            estimate_cost=data.get("estimate_cost", 1.0)
        )
        resp.response_id = data.get("response_id", str(uuid.uuid4()))
        resp.timestamp = data.get("timestamp", int(time.time()))
        return resp

    def __repr__(self) -> str:
        """Return string representation of the response."""
        return (
            f"<Response {self.response_id[:6]} from {self.responder_id}, "
            f"score={self.match_score}, cost={self.estimate_cost}>"
        )
