#!/usr/bin/env python3
# FC3 Custom Server Implementation
import socket
import threading
import logging
import json
import os
import time
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fc3_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("FC3Server")

# Server configuration
SERVER_PORT = 33333  # Default port
MAX_PLAYERS = 32
SERVER_NAME = "Custom FC3 Server"
PROTOCOL_VERSION = 1.0
DB_PATH = "fc3_server.db"

# Game constants
GAME_MODES = {
    1: "Team Deathmatch",
    2: "Domination",
    3: "Firestorm"
}

@dataclass
class Player:
    id: int
    name: str
    ip: str
    port: int
    session_id: str
    last_ping: float
    score: int = 0
    team: int = 0
    connected: bool = True

@dataclass
class GameSession:
    id: str
    name: str
    host_id: int
    max_players: int
    game_mode: int
    map_name: str
    created_at: float
    players: Dict[int, Player] = None
    password: str = ""
    
    def __post_init__(self):
        if self.players is None:
            self.players = {}
            
    def add_player(self, player: Player) -> bool:
        if len(self.players) >= self.max_players:
            return False
        self.players[player.id] = player
        return True
        
    def remove_player(self, player_id: int) -> bool:
        if player_id in self.players:
            del self.players[player_id]
            return True
        return False
        
    def is_empty(self) -> bool:
        return len(self.players) == 0


class FC3Server:
    def __init__(self, config_path="fc3_server.ini"):
        self.config = self._load_config(config_path)
        self.port = self.config.get("server", {}).get("port", SERVER_PORT)
        self.max_players = self.config.get("server", {}).get("max_players", MAX_PLAYERS)
        self.server_name = self.config.get("server", {}).get("name", SERVER_NAME)
        
        self.socket = None
        self.running = False
        self.sessions: Dict[str, GameSession] = {}
        self.players: Dict[int, Player] = {}
        self.next_player_id = 1
        
        # Initialize database
        self._init_database()
        
    def _load_config(self, config_path):
        import configparser
        import json
        
        config = {
            "server": {
                "port": SERVER_PORT,
                "max_players": MAX_PLAYERS,
                "name": SERVER_NAME
            },
            "game": {
                "maps": ["Tropical Island", "Jungle", "Mountain Base", "Beach"],
                "default_mode": 1
            }
        }
        
        if os.path.exists(config_path):
            try:
                parser = configparser.ConfigParser()
                parser.read(config_path)
                
                if "server" in parser:
                    for key in parser["server"]:
                        if key == "port":
                            config["server"]["port"] = parser.getint("server", key)
                        elif key == "max_players":
                            config["server"]["max_players"] = parser.getint("server", key)
                        else:
                            config["server"][key] = parser.get("server", key)
                            
                if "game" in parser:
                    if "maps" in parser["game"]:
                        maps_str = parser.get("game", "maps")
                        config["game"]["maps"] = json.loads(maps_str)
                    if "default_mode" in parser["game"]:
                        config["game"]["default_mode"] = parser.getint("game", "default_mode")
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                
        # Create default config if it doesn't exist
        if not os.path.exists(config_path):
            self._save_config(config, config_path)
                
        return config
    
    def _save_config(self, config, config_path):
        import configparser
        import json
        
        parser = configparser.ConfigParser()
        
        for section in config:
            parser[section] = {}
            for key, value in config[section].items():
                if isinstance(value, list):
                    parser[section][key] = json.dumps(value)
                else:
                    parser[section][key] = str(value)
        
        with open(config_path, 'w') as f:
            parser.write(f)
    
    def _init_database(self):
        """Initialize SQLite database for persistent storage"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            last_ip TEXT,
            last_session TEXT,
            last_seen TIMESTAMP,
            total_games INTEGER DEFAULT 0,
            total_score INTEGER DEFAULT 0
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            game_mode INTEGER NOT NULL,
            map_name TEXT NOT NULL,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            player_count INTEGER NOT NULL
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def start(self):
        """Start the server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', self.port))
        self.running = True
        
        logger.info(f"FC3 Server started on port {self.port}")
        logger.info(f"Server name: {self.server_name}")
        
        # Start maintenance thread
        threading.Thread(target=self._maintenance_loop, daemon=True).start()
        
        # Main server loop
        try:
            while self.running:
                try:
                    data, addr = self.socket.recvfrom(4096)
                    threading.Thread(target=self._handle_packet, args=(data, addr), daemon=True).start()
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.socket:
            self.socket.close()
        logger.info("Server stopped")
    
    def _maintenance_loop(self):
        """Background maintenance thread to clean up stale sessions and players"""
        while self.running:
            try:
                current_time = time.time()
                
                # Remove players who haven't pinged in 30 seconds
                stale_players = []
                for player_id, player in self.players.items():
                    if current_time - player.last_ping > 30:
                        stale_players.append(player_id)
                        logger.info(f"Player {player.name} (ID: {player.id}) timed out")
                
                for player_id in stale_players:
                    self._remove_player(player_id)
                
                # Remove empty sessions
                empty_sessions = [session_id for session_id, session in self.sessions.items() 
                                if session.is_empty()]
                for session_id in empty_sessions:
                    logger.info(f"Removing empty session {session_id}")
                    del self.sessions[session_id]
                
            except Exception as e:
                logger.error(f"Error in maintenance loop: {e}")
            
            # Run maintenance every 5 seconds
            time.sleep(5)
    
    def _handle_packet(self, data: bytes, addr: Tuple[str, int]):
        """Process incoming packet from a client"""
        try:
            # Decode packet (simplified format for this example)
            # In a real implementation, you'd need proper protocol parsing
            message = data.decode('utf-8').strip()
            parts = message.split('|')
            cmd = parts[0]
            
            ip, port = addr
            
            # Handle different message types
            if cmd == "PING":
                self._handle_ping(parts, addr)
            elif cmd == "REGISTER":
                self._handle_register(parts, addr)
            elif cmd == "CREATE_SESSION":
                self._handle_create_session(parts, addr)
            elif cmd == "JOIN_SESSION":
                self._handle_join_session(parts, addr)
            elif cmd == "LEAVE_SESSION":
                self._handle_leave_session(parts, addr)
            elif cmd == "LIST_SESSIONS":
                self._handle_list_sessions(addr)
            elif cmd == "GAME_UPDATE":
                self._handle_game_update(parts, addr)
            else:
                logger.warning(f"Unknown command: {cmd} from {addr}")
        
        except Exception as e:
            logger.error(f"Error handling packet: {e}")
    
    def _handle_ping(self, parts, addr):
        """Handle ping requests from clients"""
        if len(parts) < 2:
            return
            
        player_id = int(parts[1])
        if player_id in self.players:
            self.players[player_id].last_ping = time.time()
            self.socket.sendto(b"PONG", addr)
    
    def _handle_register(self, parts, addr):
        """Register a new player"""
        if len(parts) < 2:
            return
            
        player_name = parts[1]
        ip, port = addr
        
        # Create new player
        player_id = self.next_player_id
        self.next_player_id += 1
        
        session_id = ""  # No session initially
        
        player = Player(
            id=player_id,
            name=player_name,
            ip=ip,
            port=port,
            session_id=session_id,
            last_ping=time.time()
        )
        
        self.players[player_id] = player
        logger.info(f"Registered new player: {player_name} (ID: {player_id}) from {ip}:{port}")
        
        # Send registration confirmation
        response = f"REGISTER_OK|{player_id}|{player_name}"
        self.socket.sendto(response.encode('utf-8'), addr)
        
        # Store in database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO players (id, name, last_ip, last_seen) VALUES (?, ?, ?, datetime('now'))",
            (player_id, player_name, ip)
        )
        conn.commit()
        conn.close()
    
    def _handle_create_session(self, parts, addr):
        """Create a new game session"""
        if len(parts) < 5:
            return
            
        player_id = int(parts[1])
        session_name = parts[2]
        game_mode = int(parts[3])
        map_name = parts[4]
        
        if player_id not in self.players:
            return
            
        # Generate unique session ID
        import uuid
        session_id = str(uuid.uuid4())
        
        # Create session
        session = GameSession(
            id=session_id,
            name=session_name,
            host_id=player_id,
            max_players=16,  # Default for FC3
            game_mode=game_mode,
            map_name=map_name,
            created_at=time.time()
        )
        
        # Add host to session
        player = self.players[player_id]
        player.session_id = session_id
        session.add_player(player)
        
        # Store session
        self.sessions[session_id] = session
        
        logger.info(f"Created new session: {session_name} (ID: {session_id}) by {player.name}")
        
        # Send confirmation
        response = f"SESSION_CREATED|{session_id}|{session_name}"
        self.socket.sendto(response.encode('utf-8'), addr)
    
    def _handle_join_session(self, parts, addr):
        """Handle a player joining a session"""
        if len(parts) < 3:
            return
            
        player_id = int(parts[1])
        session_id = parts[2]
        
        if player_id not in self.players or session_id not in self.sessions:
            response = "JOIN_FAILED|Session not found"
            self.socket.sendto(response.encode('utf-8'), addr)
            return
            
        player = self.players[player_id]
        session = self.sessions[session_id]
        
        # Check if session is full
        if len(session.players) >= session.max_players:
            response = "JOIN_FAILED|Session is full"
            self.socket.sendto(response.encode('utf-8'), addr)
            return
            
        # Add player to session
        player.session_id = session_id
        session.add_player(player)
        
        logger.info(f"Player {player.name} joined session {session.name}")
        
        # Send all session information to the joining player
        players_info = []
        for p in session.players.values():
            players_info.append(f"{p.id}:{p.name}:{p.team}:{p.score}")
            
        players_str = ",".join(players_info)
        
        response = f"JOIN_OK|{session_id}|{session.name}|{session.game_mode}|{session.map_name}|{players_str}"
        self.socket.sendto(response.encode('utf-8'), addr)
        
        # Notify all other players in the session
        self._broadcast_to_session(
            session_id,
            f"PLAYER_JOINED|{player.id}|{player.name}",
            exclude_player=player_id
        )
    
    def _handle_leave_session(self, parts, addr):
        """Handle a player leaving a session"""
        if len(parts) < 3:
            return
            
        player_id = int(parts[1])
        session_id = parts[2]
        
        if player_id not in self.players or session_id not in self.sessions:
            return
            
        player = self.players[player_id]
        session = self.sessions[session_id]
        
        # Remove player from session
        if session.remove_player(player_id):
            player.session_id = ""
            logger.info(f"Player {player.name} left session {session.name}")
            
            # Notify all other players in the session
            self._broadcast_to_session(
                session_id,
                f"PLAYER_LEFT|{player.id}|{player.name}",
                exclude_player=player_id
            )
            
            # If host left, assign new host or close session
            if player_id == session.host_id and not session.is_empty():
                # Assign first remaining player as host
                new_host_id = next(iter(session.players.keys()))
                session.host_id = new_host_id
                
                # Notify all players of new host
                self._broadcast_to_session(
                    session_id,
                    f"NEW_HOST|{new_host_id}"
                )
            
            # Confirm to the leaving player
            response = f"LEAVE_OK|{session_id}"
            self.socket.sendto(response.encode('utf-8'), addr)
    
    def _handle_list_sessions(self, addr):
        """Send list of active sessions to client"""
        sessions_info = []
        
        for session_id, session in self.sessions.items():
            session_str = f"{session_id}|{session.name}|{session.game_mode}|{session.map_name}|{len(session.players)}/{session.max_players}"
            sessions_info.append(session_str)
            
        sessions_list = ";".join(sessions_info)
        response = f"SESSIONS_LIST|{len(self.sessions)}|{sessions_list}"
        
        self.socket.sendto(response.encode('utf-8'), addr)
    
    def _handle_game_update(self, parts, addr):
        """Handle game state updates from clients"""
        if len(parts) < 4:
            return
            
        player_id = int(parts[1])
        session_id = parts[2]
        update_type = parts[3]
        
        if player_id not in self.players or session_id not in self.sessions:
            return
            
        player = self.players[player_id]
        session = self.sessions[session_id]
        
        # Process different update types
        if update_type == "SCORE":
            if len(parts) < 5:
                return
                
            score = int(parts[4])
            player.score = score
            
            # Broadcast score update to all players in session
            self._broadcast_to_session(
                session_id,
                f"SCORE_UPDATE|{player_id}|{score}"
            )
        
        elif update_type == "TEAM":
            if len(parts) < 5:
                return
                
            team = int(parts[4])
            player.team = team
            
            # Broadcast team update to all players in session
            self._broadcast_to_session(
                session_id,
                f"TEAM_UPDATE|{player_id}|{team}"
            )
        
        elif update_type == "GAME_EVENT":
            if len(parts) < 5:
                return
                
            event_data = parts[4]
            
            # Broadcast game event to all players in session
            self._broadcast_to_session(
                session_id,
                f"GAME_EVENT|{player_id}|{event_data}"
            )
    
    def _remove_player(self, player_id):
        """Remove a player and update any sessions they're in"""
        if player_id not in self.players:
            return
            
        player = self.players[player_id]
        
        # If player is in a session, remove them
        if player.session_id and player.session_id in self.sessions:
            session = self.sessions[player.session_id]
            session.remove_player(player_id)
            
            # Notify other players
            self._broadcast_to_session(
                player.session_id,
                f"PLAYER_LEFT|{player_id}|{player.name}",
                exclude_player=player_id
            )
            
            # If host left, assign new host or close session
            if player_id == session.host_id and not session.is_empty():
                # Assign first remaining player as host
                new_host_id = next(iter(session.players.keys()))
                session.host_id = new_host_id
                
                # Notify all players of new host
                self._broadcast_to_session(
                    player.session_id,
                    f"NEW_HOST|{new_host_id}"
                )
        
        # Update database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE players SET last_seen = datetime('now') WHERE id = ?",
            (player_id,)
        )
        conn.commit()
        conn.close()
        
        # Remove player
        del self.players[player_id]
        logger.info(f"Removed player {player.name} (ID: {player_id})")
    
    def _broadcast_to_session(self, session_id, message, exclude_player=None):
        """Send a message to all players in a session"""
        if session_id not in self.sessions:
            return
            
        session = self.sessions[session_id]
        
        encoded_message = message.encode('utf-8')
        
        for player_id, player in session.players.items():
            if exclude_player is not None and player_id == exclude_player:
                continue
                
            addr = (player.ip, player.port)
            try:
                self.socket.sendto(encoded_message, addr)
            except Exception as e:
                logger.error(f"Failed to send message to player {player.name}: {e}")


if __name__ == "__main__":
    server = FC3Server()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()