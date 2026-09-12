"""NS-3 coordinator socket communication.

Protocol (must match fl-sim-interface.h COMMAND struct):
  - Command struct: { uint32_t command, uint32_t nItems }
  - Type 1 (RUN_SIMULATION): followed by nItems × uint32_t participation flags
  - Type 2 (EXIT): close connection
  
Response from NS3 (sync mode):
  - Command struct: { RESPONSE=0, nItems }
  - Followed by nItems × Message { uint64_t id, double roundTime, double throughput }

For async mode, NS3 sends per-client AsyncMessage after each client finishes.
"""
import time
import socket
import struct
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class NS3Coordinator:
    """Manages communication with NS-3 network simulator."""
    
    def __init__(self, host: str = "localhost", port: int = 9099, use_ns3: bool = True):
        self.host = host
        self.port = port
        self.use_ns3 = use_ns3
        self.sock: Optional[socket.socket] = None
        self.connected = False
    
    def connect(self, retries: int = 120, delay: float = 0.5) -> bool:
        """Connect to NS3 socket server."""
        if not self.use_ns3:
            logger.info("NS3 disabled")
            return False
        
        for attempt in range(retries):
            try:
                self.sock = socket.create_connection((self.host, self.port), timeout=2.0)
                self.sock.settimeout(30.0)
                self.connected = True
                logger.info(f"Connected to NS3 at {self.host}:{self.port}")
                return True
            except (OSError, socket.error):
                if attempt < retries - 1:
                    time.sleep(delay)
        
        logger.warning("NS3 not available - running without network emulation")
        return False
    
    def send_round_start(self, num_clients: int, total_nodes: int, participating: List[int]) -> bool:
        """Send round start signal (Type 1 = RUN_SIMULATION).
        
        Wire format: COMMAND{1, num_clients} + num_clients × uint32(0|1)
        """
        if not self.connected or not self.sock:
            return False
        
        try:
            # Send command header: type=1 (RUN_SIMULATION), nItems=num_clients
            self.sock.sendall(struct.pack("=II", 1, num_clients))
            # Send participation flags for each client
            for client_id in range(num_clients):
                flag = 1 if client_id in participating else 0
                self.sock.sendall(struct.pack("=I", flag))
            return True
        except Exception as e:
            logger.error(f"Error sending round start: {e}")
            self._reconnect()
            return False
    
    def send_async_update(self, client_id: int, iteration: int, total_clients: int) -> bool:
        """Notify NS3 of async client update.
        
        In async mode, we send a round start for a single client.
        Wire format: COMMAND{1, total_clients} + flags (only client_id=1, rest=0)
        """
        if not self.connected or not self.sock:
            return False
        
        try:
            # Send as a single-client round simulation
            self.sock.sendall(struct.pack("=II", 1, total_clients))
            for cid in range(total_clients):
                flag = 1 if cid == client_id else 0
                self.sock.sendall(struct.pack("=I", flag))
            return True
        except Exception as e:
            logger.error(f"Error sending async update: {e}")
            self._reconnect()
            return False
    
    def receive_round_stats(self, num_clients: int) -> Dict:
        """Receive network statistics from NS3 after a round.
        
        NS3 sends: COMMAND{0=RESPONSE, nItems} + nItems × Message{uint64 id, double time, double throughput}
        """
        if not self.connected or not self.sock:
            return {}
        
        stats = {}
        try:
            # Read response header
            header = self._recv_exact(8)
            if not header:
                return {}
            resp_type, n_items = struct.unpack("=II", header)
            
            if resp_type != 0:  # Not RESPONSE
                logger.warning(f"Unexpected response type: {resp_type}")
                return {}
            
            # Read per-client messages: {uint64_t id, double roundTime, double throughput}
            msg_size = struct.calcsize("=Qdd")  # 8 + 8 + 8 = 24 bytes
            for _ in range(n_items):
                data = self._recv_exact(msg_size)
                if not data:
                    break
                cid, round_time, throughput = struct.unpack("=Qdd", data)
                stats[cid] = {
                    "ns3_time_ms": round_time * 1000,
                    "throughput_mbps": throughput / 1000.0  # kbps → Mbps
                }
        except Exception as e:
            logger.error(f"Error receiving round stats: {e}")
        
        return stats
    
    def send_exit(self):
        """Send exit signal (Type 2) and close connection."""
        if self.sock:
            try:
                self.sock.sendall(struct.pack("=II", 2, 0))
            except Exception:
                pass
            finally:
                self.sock.close()
                self.sock = None
        self.connected = False
    
    def _recv_exact(self, n: int) -> Optional[bytes]:
        """Receive exactly n bytes from socket."""
        if not self.sock:
            return None
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                return None
            buf += chunk
        return buf
    
    def _reconnect(self):
        """Try to reconnect after an error."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None
        self.connected = False
        logger.warning("NS3 connection lost, attempting reconnect...")
        self.connect(retries=5, delay=1.0)


# Legacy module-level functions for backward compatibility
_global_coordinator: Optional[NS3Coordinator] = None


def init(host: str, port: int, use_ns3: bool = True):
    """Initialize global NS3 coordinator (legacy compatibility)."""
    global _global_coordinator
    _global_coordinator = NS3Coordinator(host, port, use_ns3)


def connect(retries: int = 120, delay: float = 0.5) -> bool:
    """Connect to NS3 (legacy compatibility)."""
    if _global_coordinator is None:
        raise RuntimeError("NS3Coordinator not initialized. Call init() first.")
    return _global_coordinator.connect(retries, delay)


def send_round_start(num_clients: int, total_nodes: int, participating: List[int]) -> bool:
    """Send round start (legacy compatibility)."""
    if _global_coordinator is None:
        return False
    return _global_coordinator.send_round_start(num_clients, total_nodes, participating)


def send_async_update(client_id: int, iteration: int, total_clients: int) -> bool:
    """Send async update (legacy compatibility)."""
    if _global_coordinator is None:
        return False
    return _global_coordinator.send_async_update(client_id, iteration, total_clients)


def receive_round_stats(num_clients: int) -> Dict:
    """Receive round stats (legacy compatibility)."""
    if _global_coordinator is None:
        return {}
    return _global_coordinator.receive_round_stats(num_clients)


def send_exit():
    """Send exit (legacy compatibility)."""
    if _global_coordinator is not None:
        _global_coordinator.send_exit()
