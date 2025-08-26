"""Network Adapter for Symphony Node Communication

Provides TCP-based network communication capabilities for Symphony distributed computing nodes.
Handles message serialization, connection management, and protocol implementation.
"""

import socket
import json
import threading
from typing import Dict, Callable, List, Optional, Tuple
from dataclasses import asdict
import time


class NetworkAdapter:
    """Network adapter handling TCP communication between Symphony nodes.
    
    Provides reliable TCP-based messaging with automatic serialization/deserialization,
    neighbor management, and message handling capabilities.
    
    Attributes:
        node_id (str): Unique identifier for this node
        host (str): Host address to bind server socket
        port (int): Port number to bind server socket
        neighbors (Dict[str, Tuple[str, int]]): Registered neighbor nodes mapping
        handlers (Dict[str, Callable]): Message type handlers mapping
        server_socket (socket.socket): TCP server socket for incoming connections
        receive_thread (threading.Thread): Background thread for message reception
    """
    
    def __init__(self, node_id: str, config: dict):
        """Initialize network adapter with configuration.
        
        Args:
            node_id (str): Unique node identifier
            config (dict): Configuration dictionary containing:
                - network.host: Host address to bind
                - network.port: Port number to bind
        """
        self.node_id = node_id
        self.host = config["network"]["host"]
        self.port = config["network"]["port"]
        self.neighbors: Dict[str, Tuple[str, int]] = {}  # Node ID → (host, port)
        self.handlers: Dict[str, Callable] = {}
        self.server_socket = None
        self.receive_thread = None
        self._start_server()  # Start receiving thread

    def register_handler(self, msg_type: str, handler: Callable):
        """Register message handler for specific message type.
        
        Args:
            msg_type (str): Message type to handle (e.g., "beacon", "task_contract")
            handler (Callable): Handler function that takes (sender_id, data) as arguments
        """
        self.handlers[msg_type] = handler

    def add_neighbor(self, node_id: str, host: str, port: int):
        """Add a neighbor node to the network topology.
        
        Args:
            node_id (str): Unique identifier of the neighbor node
            host (str): Hostname or IP address of the neighbor
            port (int): Port number the neighbor is listening on
        """
        self.neighbors[node_id] = (host, port)

    def send(self, target_id: str, msg_type: str, data) -> bool:
        """Send message to target node.
        
        Establishes TCP connection, sends message with proper framing,
        and handles response acknowledgment.
        
        Args:
            target_id (str): Target node identifier
            msg_type (str): Message type (e.g., "beacon", "task_contract")
            data: Data object to send (must support JSON serialization)
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        if target_id not in self.neighbors:
            print(f"Error: Unknown node ID {target_id}")
            return False
            
        host, port = self.neighbors[target_id]
        
        try:
            # Build message packet
            message = {
                "sender_id": self.node_id,
                "target_id": target_id,
                "msg_type": msg_type,
                "data": data.to_dict(),
                "timestamp": time.time()
            }
            
            # Create TCP connection and send message
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)  # Set timeout to 5 seconds
                s.connect((host, port))
                
                # Convert message to JSON and encode as bytes
                msg_json = json.dumps(message)
                msg_bytes = msg_json.encode('utf-8')
                
                # Send message length prefix (4-byte integer)
                s.sendall(len(msg_bytes).to_bytes(4, 'big'))
                # Send message content
                s.sendall(msg_bytes)
                
                # Receive response (optional)
                response = self._receive_response(s)
                return response.get("status") == "success"
                
        except (socket.error, json.JSONDecodeError) as e:
            print(f"Failed to send message to {target_id}: {e}")
            return False

    def broadcast(self, msg_type: str, data, exclude: List[str] = None):
        """Broadcast message to all neighbors with optional exclusions.
        
        Args:
            msg_type (str): Message type to broadcast
            data: Message data to send
            exclude (List[str], optional): List of node IDs to exclude from broadcast
        """
        exclude = exclude or []
        for neighbor_id in list(self.neighbors.keys()):
            if neighbor_id not in exclude:
                self.send(neighbor_id, msg_type, data)

    def _start_server(self):
        """Start server thread to receive incoming messages.
        
        Creates TCP server socket, binds to configured address, and starts
        background thread for handling incoming connections.
        """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        
        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.receive_thread.start()
        print(f"Node {self.node_id} network adapter started, listening on {self.host}:{self.port}")

    def _receive_loop(self):
        """Message receiving loop running in background thread.
        
        Accepts incoming connections, receives complete messages with proper framing,
        and dispatches to appropriate message handlers.
        """
        while True:
            try:
                conn, addr = self.server_socket.accept()
                with conn:
                    # Receive message length prefix
                    len_bytes = conn.recv(4)
                    if not len_bytes:
                        continue
                        
                    msg_length = int.from_bytes(len_bytes, 'big')
                    
                    # Receive complete message
                    msg_bytes = b""
                    while len(msg_bytes) < msg_length:
                        chunk = conn.recv(min(4096, msg_length - len(msg_bytes)))
                        if not chunk:
                            break
                        msg_bytes += chunk
                        
                    if len(msg_bytes) != msg_length:
                        continue
                        
                    # Parse message
                    msg_json = msg_bytes.decode('utf-8')
                    message = json.loads(msg_json)
                    
                    # Send acknowledgment response
                    ack_response = {"status": "success", "message": "received"}
                    ack_json = json.dumps(ack_response)
                    ack_bytes = ack_json.encode('utf-8')
                    conn.sendall(len(ack_bytes).to_bytes(4, 'big'))
                    conn.sendall(ack_bytes)
                    
                    # Call corresponding message handler
                    self._handle_message(message)
                    
            except Exception as e:
                print(f"Error receiving message: {e}")

    def _handle_message(self, message):
        """Handle received message by dispatching to appropriate handler.
        
        Args:
            message (dict): Received message dictionary containing:
                - msg_type: Message type string
                - sender_id: Sender node identifier
                - data: Message payload data
        """
        msg_type = message.get("msg_type")
        sender_id = message.get("sender_id")
        data = message.get("data")

        if not msg_type or not sender_id or data is None:
            print(f"Invalid message format: {message}")
            return
            
        if msg_type in self.handlers:
            # Deserialize data
            deserialized_data = self._deserialize_data(data)
            self.handlers[msg_type](sender_id, deserialized_data)
        else:
            print(f"Unknown message type: {msg_type}")

    def _receive_response(self, socket_obj) -> Dict:
        """Receive and parse response message from socket.
        
        Args:
            socket_obj (socket.socket): Socket object to receive from
            
        Returns:
            Dict: Response dictionary with status and message information
        """
        try:
            # Receive response length prefix
            len_bytes = socket_obj.recv(4)
            if not len_bytes:
                return {"status": "error", "message": "No response"}
                
            resp_length = int.from_bytes(len_bytes, 'big')
            
            # Receive complete response
            resp_bytes = b""
            while len(resp_bytes) < resp_length:
                chunk = socket_obj.recv(min(4096, resp_length - len(resp_bytes)))
                if not chunk:
                    break
                resp_bytes += chunk
                
            if len(resp_bytes) != resp_length:
                return {"status": "error", "message": "Incomplete response"}
                
            # Parse response
            resp_json = resp_bytes.decode('utf-8')
            return json.loads(resp_json)
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _serialize_data(self, data):
        """Serialize data object for transmission.
        
        Supports dataclass instances and other JSON-serializable objects.
        
        Args:
            data: Data object to serialize
            
        Returns:
            Serialized data suitable for JSON encoding
        """
        if hasattr(data, "__dict__"):  # Handle class instances
            return asdict(data)
        return data

    def _deserialize_data(self, data):
        """Deserialize data object after reception.
        
        Args:
            data: Serialized data to deserialize
            
        Returns:
            Deserialized data object
            
        Note:
            Current implementation is simplified. In practice, should deserialize
            based on data type information in message header.
        """
        return data  # Simplified implementation

    def close(self):
        """Close network adapter and clean up resources.
        
        Shuts down server socket and terminates background threads.
        """
        if self.server_socket:
            self.server_socket.close()
        print(f"Node {self.node_id} network adapter closed")
