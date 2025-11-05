"""
Server registry management for keprompt HTTP servers.

Provides functions to register, track, and manage multiple keprompt server instances
running in different directories.
"""

import os
import socket
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from peewee import DoesNotExist, DatabaseProxy

from .database import ServerRegistry, create_database_from_url
from .process_utils import is_process_alive, is_keprompt_server, send_signal_to_process


# Global registry database - stored in ~/.keprompt/servers.db
_registry_db = None
_registry_proxy = DatabaseProxy()


def get_registry_database():
    """Get or create the global server registry database."""
    global _registry_db
    
    if _registry_db is None:
        # Store registry in user's home directory
        registry_path = Path.home() / '.keprompt' / 'servers.db'
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create database connection
        registry_url = f'sqlite:///{registry_path}'
        _registry_db = create_database_from_url(registry_url)
        
        # Initialize the proxy
        _registry_proxy.initialize(_registry_db)
        
        # Temporarily point ServerRegistry to this database
        original_db = ServerRegistry._meta.database
        ServerRegistry._meta.database = _registry_db
        
        # Create table if it doesn't exist
        with _registry_db:
            _registry_db.create_tables([ServerRegistry], safe=True)
        
        # Restore original database reference
        ServerRegistry._meta.database = original_db
    
    return _registry_db


def sync_registry() -> None:
    """
    Synchronize registry state with actual running processes.
    
    Updates all 'running' entries to 'died' if their process no longer exists.
    This is called automatically before every server operation to ensure
    the registry always reflects reality.
    """
    db = get_registry_database()
    
    with db.atomic():
        # Temporarily point ServerRegistry to registry database
        original_db = ServerRegistry._meta.database
        ServerRegistry._meta.database = db
        
        try:
            running_servers = ServerRegistry.select().where(ServerRegistry.status == 'running')
            
            for server in running_servers:
                # Check if process is still alive
                if not is_process_alive(server.pid):
                    server.status = 'died'
                    server.died_at = datetime.now()
                    server.save()
                # Optional: verify it's actually a keprompt process
                elif not is_keprompt_server(server.pid):
                    server.status = 'died'
                    server.died_at = datetime.now()
                    server.save()
        finally:
            # Restore original database reference
            ServerRegistry._meta.database = original_db


def register_server(directory: str, port: int, pid: int, web_gui_enabled: bool = False) -> ServerRegistry:
    """
    Register a new server in the global registry.
    
    Args:
        directory: Absolute path to the server's working directory
        port: Port the server is running on
        pid: Process ID of the server
        web_gui_enabled: Whether the server has web GUI enabled
        
    Returns:
        The created ServerRegistry entry
    """
    db = get_registry_database()
    
    # Normalize directory path
    directory = str(Path(directory).resolve())
    
    with db.atomic():
        # Temporarily point ServerRegistry to registry database
        original_db = ServerRegistry._meta.database
        ServerRegistry._meta.database = db
        
        try:
            # Check if entry already exists
            try:
                existing = ServerRegistry.get(ServerRegistry.directory == directory)
                # Update existing entry
                existing.port = port
                existing.pid = pid
                existing.status = 'running'
                existing.started_at = datetime.now()
                existing.died_at = None
                existing.web_gui_enabled = web_gui_enabled
                existing.save()
                return existing
            except DoesNotExist:
                # Create new entry
                server = ServerRegistry.create(
                    directory=directory,
                    port=port,
                    pid=pid,
                    status='running',
                    started_at=datetime.now(),
                    web_gui_enabled=web_gui_enabled
                )
                return server
        finally:
            # Restore original database reference
            ServerRegistry._meta.database = original_db


def unregister_server(directory: str) -> bool:
    """
    Remove a server from the registry (clean shutdown).
    
    Args:
        directory: Absolute path to the server's working directory
        
    Returns:
        True if server was found and removed, False otherwise
    """
    db = get_registry_database()
    
    # Normalize directory path
    directory = str(Path(directory).resolve())
    
    with db.atomic():
        # Temporarily point ServerRegistry to registry database
        original_db = ServerRegistry._meta.database
        ServerRegistry._meta.database = db
        
        try:
            try:
                server = ServerRegistry.get(ServerRegistry.directory == directory)
                server.delete_instance()
                return True
            except DoesNotExist:
                return False
        finally:
            # Restore original database reference
            ServerRegistry._meta.database = original_db


def get_server(directory: str) -> Optional[ServerRegistry]:
    """
    Get server information for a specific directory.
    
    Args:
        directory: Absolute path to the server's working directory
        
    Returns:
        ServerRegistry entry if found, None otherwise
    """
    db = get_registry_database()
    
    # Normalize directory path
    directory = str(Path(directory).resolve())
    
    # Temporarily point ServerRegistry to registry database
    original_db = ServerRegistry._meta.database
    ServerRegistry._meta.database = db
    
    try:
        try:
            return ServerRegistry.get(ServerRegistry.directory == directory)
        except DoesNotExist:
            return None
    finally:
        # Restore original database reference
        ServerRegistry._meta.database = original_db


def list_servers(all_servers: bool = False, active_only: bool = False) -> List[ServerRegistry]:
    """
    List registered servers.
    
    Args:
        all_servers: If True, return all servers. If False, return only current directory
        active_only: If True, return only servers with status='running'
        
    Returns:
        List of ServerRegistry entries
    """
    db = get_registry_database()
    
    # Temporarily point ServerRegistry to registry database
    original_db = ServerRegistry._meta.database
    ServerRegistry._meta.database = db
    
    try:
        if all_servers:
            query = ServerRegistry.select().order_by(ServerRegistry.started_at.desc())
        else:
            directory = str(Path.cwd().resolve())
            query = ServerRegistry.select().where(ServerRegistry.directory == directory)
        
        if active_only:
            query = query.where(ServerRegistry.status == 'running')
        
        return list(query)
    finally:
        # Restore original database reference
        ServerRegistry._meta.database = original_db


def find_free_port(start_port: int = 8080) -> int:
    """
    Find a free port starting from start_port.
    
    Checks both the registry and actual port availability.
    
    Args:
        start_port: Port to start searching from
        
    Returns:
        First available port number
    """
    db = get_registry_database()
    
    # Temporarily point ServerRegistry to registry database
    original_db = ServerRegistry._meta.database
    ServerRegistry._meta.database = db
    
    try:
        # Get all ports used by running servers
        running_servers = ServerRegistry.select().where(ServerRegistry.status == 'running')
        used_ports = {server.port for server in running_servers}
        
        # Find first available port
        port = start_port
        while port < 65535:
            if port not in used_ports and is_port_available(port):
                return port
            port += 1
        
        raise RuntimeError("No available ports found")
    finally:
        # Restore original database reference
        ServerRegistry._meta.database = original_db


def is_port_available(port: int) -> bool:
    """
    Check if a port is available for binding.
    
    Args:
        port: Port number to check
        
    Returns:
        True if port is available, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', port))
            return True
    except OSError:
        return False


def stop_server(directory: str) -> bool:
    """
    Stop a server by sending SIGTERM to its process.
    
    Args:
        directory: Absolute path to the server's working directory
        
    Returns:
        True if signal was sent successfully, False otherwise
    """
    server = get_server(directory)
    
    if not server:
        return False
    
    if server.status != 'running':
        return False
    
    # Send SIGTERM for graceful shutdown
    import signal
    return send_signal_to_process(server.pid, signal.SIGTERM)


def get_target_directories(all_servers: bool, directory: Optional[str]) -> List[str]:
    """
    Determine which directories to operate on based on flags.
    
    Args:
        all_servers: If True, return all registered directories
        directory: If specified, return this directory (overrides all_servers)
        
    Returns:
        List of directory paths
    """
    if directory:
        # Explicit directory specified
        return [str(Path(directory).resolve())]
    elif all_servers:
        # All registered servers
        servers = list_servers(all_servers=True)
        return [server.directory for server in servers]
    else:
        # Default: current directory
        return [str(Path.cwd().resolve())]
