"""
Process management utilities for server registry.

Provides functions to check process existence and validate keprompt server processes.
"""

import os
import signal
from typing import Optional, Dict, Any


def is_process_alive(pid: int) -> bool:
    """
    Check if a process with the given PID exists.
    
    Args:
        pid: Process ID to check
        
    Returns:
        True if process exists, False otherwise
    """
    try:
        # Send signal 0 - doesn't kill the process, just checks if it exists
        # If the process exists and we have permission, this succeeds
        os.kill(pid, 0)
        return True
    except OSError:
        # Process doesn't exist or we don't have permission
        return False
    except Exception:
        # Any other error, assume process is not alive
        return False


def is_keprompt_server(pid: int) -> bool:
    """
    Verify that a process is actually a keprompt server.
    
    This is an optional extra validation to ensure the PID
    corresponds to an actual keprompt process, not just any process
    that happens to have reused the PID.
    
    Args:
        pid: Process ID to check
        
    Returns:
        True if process appears to be a keprompt server, False otherwise
    """
    try:
        # Try to use psutil if available for detailed process inspection
        import psutil
        
        try:
            proc = psutil.Process(pid)
            cmdline = ' '.join(proc.cmdline())
            
            # Check if command line contains keprompt-related keywords
            keywords = ['keprompt', 'http_server', 'uvicorn']
            return any(keyword in cmdline.lower() for keyword in keywords)
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
            
    except ImportError:
        # psutil not available - fall back to basic alive check
        # This is acceptable since PID reuse is rare
        return is_process_alive(pid)


def get_process_info(pid: int) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a process.
    
    Args:
        pid: Process ID to inspect
        
    Returns:
        Dictionary with process info, or None if process doesn't exist
    """
    if not is_process_alive(pid):
        return None
    
    try:
        import psutil
        
        try:
            proc = psutil.Process(pid)
            return {
                'pid': pid,
                'name': proc.name(),
                'cmdline': ' '.join(proc.cmdline()),
                'status': proc.status(),
                'create_time': proc.create_time(),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
            
    except ImportError:
        # psutil not available - return minimal info
        return {
            'pid': pid,
            'alive': True,
        }


def send_signal_to_process(pid: int, sig: signal.Signals = signal.SIGTERM) -> bool:
    """
    Send a signal to a process.
    
    Args:
        pid: Process ID to signal
        sig: Signal to send (default: SIGTERM for graceful shutdown)
        
    Returns:
        True if signal was sent successfully, False otherwise
    """
    try:
        os.kill(pid, sig)
        return True
    except OSError:
        return False
    except Exception:
        return False
