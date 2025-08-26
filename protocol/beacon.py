# protocol/beacon.py
"""Beacon message implementation for distributed service discovery in symphony network.

This module provides the Beacon class for discovering and requesting services
across the distributed symphony network.
"""

import uuid
import time
from typing import Dict, Optional


class Beacon:
    """Beacon message for discovering and requesting services in the network.
    
    A Beacon is used to discover nodes that can fulfill specific capability
    requirements across the distributed network. It includes TTL-based
    propagation control to limit message flooding.
    
    Attributes:
        beacon_id (str): Unique identifier for this beacon message
        sender (str): DID of the node that issued this beacon
        task_id (str): Task identifier, defaults to beacon_id if not provided
        requirement (str): Brief description of the required capability
        ttl (int): Time-to-live hop count for propagation control
        timestamp (int): Unix timestamp when beacon was created
    """
    
    def __init__(
        self, 
        sender: str, 
        requirement: str, 
        task_id: Optional[str] = None, 
        ttl: int = 2
    ) -> None:
        """Initialize a Beacon instance.
        
        Args:
            sender: Node DID that issues this beacon
            requirement: Brief description of the required capability
            task_id: Task identifier. Defaults to beacon_id if not provided
            ttl: Time-to-live hop count for propagation control. Defaults to 2
        """
        self.beacon_id = str(uuid.uuid4())
        self.sender = sender
        self.task_id = task_id or self.beacon_id
        self.requirement = requirement
        self.ttl = ttl
        self.timestamp = int(time.time())

    def to_dict(self) -> Dict[str, any]:
        """Convert beacon to dictionary format for serialization.
        
        Returns:
            Dictionary representation of the beacon
        """
        return {
            "beacon_id": self.beacon_id,
            "sender": self.sender,
            "task_id": self.task_id,
            "requirement": self.requirement,
            "ttl": self.ttl,
            "timestamp": self.timestamp
        }

    @staticmethod
    def from_dict(data: Dict[str, any]) -> 'Beacon':
        """Create Beacon instance from dictionary data.
        
        Args:
            data: Dictionary containing beacon data
            
        Returns:
            Beacon instance created from the dictionary
        """
        beacon = Beacon(
            sender=data.get("sender", "unknown"),
            requirement=data.get("requirement", ""),
            task_id=data.get("task_id"),
            ttl=data.get("ttl", 2)
        )
        beacon.beacon_id = data.get("beacon_id", str(uuid.uuid4()))
        beacon.timestamp = data.get("timestamp", int(time.time()))
        return beacon

    def __repr__(self) -> str:
        """Return string representation of the beacon."""
        return (
            f"<Beacon {self.task_id[:8]} from {self.sender} "
            f"need '{self.requirement}' TTL={self.ttl}>"
        )
