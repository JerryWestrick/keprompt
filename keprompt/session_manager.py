"""
High-level session management for KePrompt.

Provides the interface between the VM and the database layer.
"""

import json
import os
import socket
import subprocess
import sys
from datetime import datetime
from typing import Dict, Any, Optional

from .database import get_db_manager, Session, CostTracking
from .version import __version__


class SessionManager:
    """High-level Session operations."""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self._hostname = socket.gethostname()
        self._git_commit = self._get_git_commit()
    
    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash if available."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                return result.stdout.strip()[:8]  # Short hash
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None
    
    def _make_serializable(self, obj):
        """Make an object JSON serializable."""
        if isinstance(obj, dict):
            return {key: self._make_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif hasattr(obj, '__class__') and obj.__class__.__name__ == 'AiModel':
            return str(obj)
        elif hasattr(obj, '__class__') and 'Path' in obj.__class__.__name__:
            return str(obj)
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            try:
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                return str(obj)
    
    def generate_session_name(self, prompt_name: str = None, prompt_version: str = None,
                              session_id: str = None, process_id: int = None) -> str:
        """Generate automatic session name using our agreed format."""
        # Get current timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Get process ID
        if process_id is None:
            process_id = os.getpid()
        
        # Sanitize prompt name
        if prompt_name:
            # Remove special characters and replace spaces with underscores
            sanitized_name = "".join(c if c.isalnum() or c in '_-' else '_' for c in prompt_name)
            sanitized_name = sanitized_name.strip('_')
        else:
            sanitized_name = "session"
        
        # Sanitize version
        if prompt_version:
            # Replace dots with underscores
            sanitized_version = prompt_version.replace('.', '_')
        else:
            sanitized_version = "0_0_0"
        
        # Format: {semantic_name}_v{version}_{timestamp}_{process_id}
        return f"{sanitized_name}_v{sanitized_version}_{timestamp}_{process_id}"
    
    def save_session(self, vm) -> str:
        """Save session from VM state."""
        
        # Prepare session data
        messages_json = json.dumps(vm.prompt.to_json())
        
        # Prepare VM state
        vm_state = {
            "ip": vm.ip,
            "model_name": vm.model_name,
            "company": vm.model.company if vm.model else "",
            "interaction_no": vm.interaction_no,
            "created": datetime.now().isoformat()
        }
        vm_state_json = json.dumps(vm_state)
        
        # Prepare variables (make serializable)
        serializable_vars = {}
        for key, value in vm.vdict.items():
            if hasattr(value, '__class__') and value.__class__.__name__ == 'AiModel':
                serializable_vars[key] = str(value)
            elif hasattr(value, '__class__') and 'Path' in value.__class__.__name__:
                serializable_vars[key] = str(value)
            elif isinstance(value, (str, int, float, bool, type(None))):
                serializable_vars[key] = value
            else:
                try:
                    json.dumps(value)
                    serializable_vars[key] = value
                except (TypeError, ValueError):
                    serializable_vars[key] = str(value)
        
        variables_json = json.dumps(serializable_vars)
        
        # Prepare metadata
        metadata = {
            'prompt_name': vm.prompt_name or "Unknown",
            'prompt_version': vm.prompt_version or "0.0.0",
            'prompt_filename': vm.filename,
            'hostname': self._hostname,
            'git_commit': self._git_commit,
            'total_api_calls': vm.interaction_no,
            'total_tokens_in': vm.toks_in,
            'total_tokens_out': vm.toks_out,
            'total_cost': float(vm.cost_in + vm.cost_out)
        }
        
        
        # Save to database
        session = self.db_manager.save_session(
            session_id=vm.prompt_uuid,
            session_name="",  # No longer used, but keep for compatibility
            messages_json=messages_json,
            vm_state_json=vm_state_json,
            variables_json=variables_json,
            **metadata
        )
        
        return vm.prompt_uuid  # Return session_id instead of session_name
    
    def save_cost_tracking(self, vm, msg_no: int, call_id: str, tokens_in: int, tokens_out: int,
                          cost_in: float, cost_out: float, elapsed_time: float, 
                          model: str, provider: str, success: bool = True, 
                          error_message: str = None, **kwargs) -> CostTracking:
        """Save cost tracking data."""
        cost_data = {
            'call_id': call_id,
            'tokens_in': tokens_in,
            'tokens_out': tokens_out,
            'cost_in': float(cost_in),
            'cost_out': float(cost_out),
            'estimated_costs': float(cost_in + cost_out),
            'elapsed_time': float(elapsed_time),
            'model': model,
            'provider': provider,
            'success': success,
            'error_message': error_message,
            'prompt_semantic_name': vm.prompt_name,
            'prompt_version_tracking': vm.prompt_version,
            'expected_params': json.dumps(vm.expected_params) if vm.expected_params else None,
            'execution_mode': getattr(vm, 'log_mode', 'production').name.lower() if hasattr(getattr(vm, 'log_mode', None), 'name') else 'production',
            'parameters': json.dumps(self._make_serializable(vm.vdict)) if vm.vdict else None,
            'environment': os.getenv('ENVIRONMENT', 'development'),
            **kwargs
        }
        
        return self.db_manager.save_cost_tracking(
            session_id=vm.prompt_uuid,
            msg_no=msg_no,
            **cost_data
        )
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session with all related data."""
        return self.db_manager.get_session_with_costs(session_id)
    
    def list_sessions(self, limit: int = 100) -> list:
        """List recent sessions."""
        sessions = self.db_manager.list_sessions(limit=limit)
        return [
            {
                'session_id': conv.session_id,
                'created_timestamp': conv.created_timestamp.isoformat() if conv.created_timestamp else '',
                'prompt_name': conv.prompt_name,
                'prompt_version': conv.prompt_version,
                'prompt_filename': conv.prompt_filename,
                'total_cost': float(conv.total_cost),
                'total_api_calls': conv.total_api_calls
            }
            for conv in sessions
        ]
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session and all related data."""
        return self.db_manager.delete_session(session_id)
    
    def cleanup_sessions(self, max_days: int = None, max_count: int = None,
                         max_size_gb: float = None) -> Dict[str, int]:
        """Clean up old sessions."""
        return self.db_manager.cleanup_old_sessions(
            max_days=max_days,
            max_count=max_count,
            max_size_gb=max_size_gb
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        return self.db_manager.get_database_stats()


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
