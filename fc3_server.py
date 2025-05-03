import socket
import threading
import time
import json
import os
import sys
import signal
import configparser
import struct
from datetime import datetime

# Current date and time: 2025-05-03 09:04:14
# Current user: Saviru

# Constants
DEFAULT_PORT = 9201
MAX_PLAYERS = 16
HEARTBEAT_INTERVAL = 30  # seconds
PLAYER_TIMEOUT = 60  # seconds
LOG_FILE = "fc3_server_log.txt"

# Packet types
PACKET_CONNECT = 1
PACKET_DISCONNECT = 2
PACKET_PLAYER_UPDATE = 3
PACKET_GAME_EVENT = 4
PACKET_CHAT_MESSAGE = 5
PACKET_HEARTBEAT = 6

class FC3MultiplayerServer:
    def __init__(self):
        # Load configuration
        self.config = configparser.ConfigParser()
        if os.path.exists('fc3_multiplayer.ini'):
            self.config.read('fc3_multiplayer.ini')
            
        self.port = self.config.getint('DEFAULT', 'server_port', fallback=DEFAULT_PORT)
        self.max_players = self.config.getint('DEFAULT', 'max_players', fallback=MAX_PLAYERS)
        self.game_name = self.config.get('DEFAULT', 'game_name', fallback="FC3 Multiplayer")
        
        # Server state
        self.running = False
        self.clients = {}  # {client_id: {'address': (ip, port), 'last_seen': timestamp, 'data': {...}}}
        self.next_client_id = 1
        self.lock = threading.Lock()
        
        # Create a UDP socket for the server
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
        
        self.log(f"Server initialized with port {self.port}, max players {self.max_players}")
        self.log(f"Game name: {self.game_name}")
    
    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        # Also write to log file
        with open(LOG_FILE, "a") as f:
            f.write(log_message + "\n")
    
    def handle_signal(self, signum, frame):
        self.log(f"Received signal {signum}, shutting down server...")
        self.stop()
    
    def start(self):
        if self.running:
            self.log("Server is already running")
            return
        
        try:
            # Bind the socket to the specified port
            self.socket.bind(('0.0.0.0', self.port))
            self.running = True
            
            self.log(f"Server started on port {self.port}")
            
            # Start heartbeat thread
            self.heartbeat_thread = threading.Thread(target=self.heartbeat_loop)
            self.heartbeat_thread.daemon = True
            self.heartbeat_thread.start()
            
            # Main server loop
            self.server_loop()
            
        except Exception as e:
            self.log(f"Error starting server: {e}")
            self.running = False
            self.socket.close()
    
    def stop(self):
        if not self.running:
            return
        
        self.log("Stopping server...")
        self.running = False
        
        # Send disconnect message to all clients
        with self.lock:
            for client_id, client_data in self.clients.items():
                self.send_packet(client_data['address'], PACKET_DISCONNECT, 
                                {"reason": "Server shutting down"})
        
        # Close socket
        self.socket.close()
        self.log("Server stopped")
    
    def heartbeat_loop(self):
        """Send periodic heartbeats and check for timeouts"""
        while self.running:
            current_time = time.time()
            
            with self.lock:
                # Check for client timeouts
                client_ids = list(self.clients.keys())
                for client_id in client_ids:
                    client_data = self.clients[client_id]
                    if current_time - client_data['last_seen'] > PLAYER_TIMEOUT:
                        self.log(f"Client {client_id} timed out")
                        self.clients.pop(client_id)
                        # Notify other clients
                        self.broadcast_player_disconnect(client_id)
                
                # Send heartbeats to all clients
                for client_id, client_data in self.clients.items():
                    self.send_packet(client_data['address'], PACKET_HEARTBEAT, 
                                   {"server_time": current_time})
            
            # Sleep until next heartbeat
            time.sleep(HEARTBEAT_INTERVAL)
    
    def server_loop(self):
        """Main server loop to handle incoming packets"""
        self.log("Server loop started")
        
        buffer_size = 8192  # Maximum packet size
        
        while self.running:
            try:
                # Receive data from clients
                data, address = self.socket.recvfrom(buffer_size)
                
                # Process the received data
                self.process_packet(data, address)
                
            except socket.error as e:
                if self.running:  # Only log errors if server is still running
                    self.log(f"Socket error: {e}")
                break
            except Exception as e:
                self.log(f"Error in server loop: {e}")
        
        self.log("Server loop ended")
    
    def process_packet(self, data, address):
        """Process an incoming packet"""
        try:
            # Basic packet format: [1 byte packet type][2 bytes data size][data bytes]
            if len(data) < 3:
                return
            
            packet_type = data[0]
            data_size = struct.unpack('!H', data[1:3])[0]
            
            if len(data) < 3 + data_size:
                return
            
            packet_data = data[3:3+data_size]
            
            # Handle the packet based on its type
            if packet_type == PACKET_CONNECT:
                self.handle_connect(packet_data, address)
            elif packet_type == PACKET_DISCONNECT:
                self.handle_disconnect(packet_data, address)
            elif packet_type == PACKET_PLAYER_UPDATE:
                self.handle_player_update(packet_data, address)
            elif packet_type == PACKET_GAME_EVENT:
                self.handle_game_event(packet_data, address)
            elif packet_type == PACKET_CHAT_MESSAGE:
                self.handle_chat_message(packet_data, address)
            elif packet_type == PACKET_HEARTBEAT:
                self.handle_heartbeat(packet_data, address)
            
        except Exception as e:
            self.log(f"Error processing packet from {address}: {e}")
    
    def handle_connect(self, packet_data, address):
        """Handle a connection request from a client"""
        try:
            # Parse client data
            client_data = json.loads(packet_data.decode('utf-8'))
            client_name = client_data.get('name', f"Player{self.next_client_id}")
            
            with self.lock:
                # Check if this client is already connected (by address)
                for client_id, data in self.clients.items():
                    if data['address'] == address:
                        # Update the last seen time
                        data['last_seen'] = time.time()
                        # Send the existing client ID back
                        self.send_packet(address, PACKET_CONNECT, {
                            "client_id": client_id,
                            "success": True,
                            "message": "Reconnected to server"
                        })
                        self.log(f"Client {client_id} ({client_name}) reconnected from {address}")
                        return
                
                # Check if server is full
                if len(self.clients) >= self.max_players:
                    self.send_packet(address, PACKET_CONNECT, {
                        "success": False,
                        "message": "Server is full"
                    })
                    self.log(f"Connection from {address} rejected - server full")
                    return
                
                # Assign a new client ID
                client_id = self.next_client_id
                self.next_client_id += 1
                
                # Store client information
                self.clients[client_id] = {
                    'address': address,
                    'last_seen': time.time(),
                    'name': client_name,
                    'data': client_data
                }
                
                # Send confirmation to the client
                self.send_packet(address, PACKET_CONNECT, {
                    "client_id": client_id,
                    "success": True,
                    "message": "Connected to server",
                    "server_name": self.game_name,
                    "player_count": len(self.clients),
                    "max_players": self.max_players
                })
                
                self.log(f"Client {client_id} ({client_name}) connected from {address}")
                
                # Broadcast new player to all other clients
                self.broadcast_player_connect(client_id, client_name)
        
        except Exception as e:
            self.log(f"Error handling connect from {address}: {e}")
            self.send_packet(address, PACKET_CONNECT, {
                "success": False,
                "message": f"Server error: {str(e)}"
            })
    
    def handle_disconnect(self, packet_data, address):
        """Handle a client disconnection"""
        client_id = None
        
        with self.lock:
            # Find the client by address
            for cid, data in self.clients.items():
                if data['address'] == address:
                    client_id = cid
                    break
            
            if client_id is not None:
                client_name = self.clients[client_id].get('name', f"Player{client_id}")
                self.clients.pop(client_id)
                self.log(f"Client {client_id} ({client_name}) disconnected")
                
                # Broadcast disconnection to other clients
                self.broadcast_player_disconnect(client_id)
    
    def handle_player_update(self, packet_data, address):
        """Handle player state update"""
        client_id = None
        
        with self.lock:
            # Find the client by address
            for cid, data in self.clients.items():
                if data['address'] == address:
                    client_id = cid
                    # Update last seen time
                    data['last_seen'] = time.time()
                    break
            
            if client_id is not None:
                try:
                    # Update player data
                    player_data = json.loads(packet_data.decode('utf-8'))
                    self.clients[client_id]['data'].update(player_data)
                    
                    # Broadcast update to all other clients
                    self.broadcast_player_update(client_id, player_data)
                except:
                    pass  # Ignore invalid update packets
    
    def handle_game_event(self, packet_data, address):
        """Handle game events like shooting, damage, etc."""
        client_id = None
        
        with self.lock:
            # Find the client by address
            for cid, data in self.clients.items():
                if data['address'] == address:
                    client_id = cid
                    data['last_seen'] = time.time()
                    break
            
            if client_id is not None:
                try:
                    # Parse and broadcast the event
                    event_data = json.loads(packet_data.decode('utf-8'))
                    event_data['source_id'] = client_id  # Add source client ID
                    
                    # Broadcast to all clients
                    for other_id, other_data in self.clients.items():
                        if other_id != client_id:  # Don't send back to source
                            self.send_packet(other_data['address'], PACKET_GAME_EVENT, event_data)
                except:
                    pass  # Ignore invalid event packets
    
    def handle_chat_message(self, packet_data, address):
        """Handle chat messages between players"""
        client_id = None
        
        with self.lock:
            # Find the client by address
            for cid, data in self.clients.items():
                if data['address'] == address:
                    client_id = cid
                    data['last_seen'] = time.time()
                    break
            
            if client_id is not None:
                try:
                    # Parse message data
                    message_data = json.loads(packet_data.decode('utf-8'))
                    sender_name = self.clients[client_id].get('name', f"Player{client_id}")
                    
                    # Add sender info
                    message_data['sender_id'] = client_id
                    message_data['sender_name'] = sender_name
                    
                    # Log the message
                    self.log(f"Chat: [{sender_name}] {message_data.get('message', '')}")
                    
                    # Broadcast to all clients
                    for other_id, other_data in self.clients.items():
                        self.send_packet(other_data['address'], PACKET_CHAT_MESSAGE, message_data)
                except:
                    pass  # Ignore invalid message packets
    
    def handle_heartbeat(self, packet_data, address):
        """Handle heartbeat packets from clients"""
        with self.lock:
            # Find the client by address
            for cid, data in self.clients.items():
                if data['address'] == address:
                    # Update last seen time
                    data['last_seen'] = time.time()
                    break
    
    def broadcast_player_connect(self, client_id, client_name):
        """Broadcast a player connection to all other clients"""
        with self.lock:
            for other_id, other_data in self.clients.items():
                if other_id != client_id:
                    self.send_packet(other_data['address'], PACKET_CONNECT, {
                        "new_player_id": client_id,
                        "new_player_name": client_name
                    })
    
    def broadcast_player_disconnect(self, client_id):
        """Broadcast a player disconnection to all other clients"""
        with self.lock:
            for other_id, other_data in self.clients.items():
                if other_id != client_id:
                    self.send_packet(other_data['address'], PACKET_DISCONNECT, {
                        "player_id": client_id
                    })
    
    def broadcast_player_update(self, client_id, player_data):
        """Broadcast a player update to all other clients"""
        with self.lock:
            # Add player_id to the data
            data_with_id = player_data.copy()
            data_with_id['player_id'] = client_id
            
            for other_id, other_data in self.clients.items():
                if other_id != client_id:
                    self.send_packet(other_data['address'], PACKET_PLAYER_UPDATE, data_with_id)
    
    def send_packet(self, address, packet_type, data):
        """Send a packet to a client"""
        try:
            # Convert data to JSON string
            json_data = json.dumps(data).encode('utf-8')
            
            # Create packet: [1 byte packet type][2 bytes data size][data bytes]
            packet = bytes([packet_type]) + struct.pack('!H', len(json_data)) + json_data
            
            # Send the packet
            self.socket.sendto(packet, address)
        except Exception as e:
            self.log(f"Error sending packet to {address}: {e}")

if __name__ == "__main__":
    server = FC3MultiplayerServer()
    server.start()