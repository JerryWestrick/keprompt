"""
Cost tracking system for KePrompt.

This module provides SQLite-based cost tracking that automatically captures
AI API usage costs, tokens, and execution metadata for all prompt executions.
"""

import json
import os
import socket
import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from .version import __version__


class CostTracker:
    """
    SQLite-based cost tracking system for KePrompt.
    
    Automatically tracks AI API costs, tokens, and execution metadata
    to prompts/costs.db database file.
    """
    
    def __init__(self, prompts_dir: str = "prompts"):
        """
        Initialize cost tracker.
        
        Args:
            prompts_dir: Directory containing prompts (where costs.db will be created)
        """
        self.prompts_dir = Path(prompts_dir)
        self.db_path = self.prompts_dir / "costs.db"
        self.conn = None
        self._ensure_database()
    
    def _ensure_database(self):
        """Ensure prompts directory and database exist with proper schema."""
        # Create prompts directory if it doesn't exist
        self.prompts_dir.mkdir(exist_ok=True)
        
        # Connect to database (creates file if doesn't exist)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        # Create table if it doesn't exist
        self._create_table()
    
    def _create_table(self):
        """Create cost_tracking table with proper schema and indexes."""
        create_sql = """
        CREATE TABLE IF NOT EXISTS cost_tracking (
            -- Primary key
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Core required fields (always populated)
            prompt_name TEXT NOT NULL,           -- {promptname}.prompt
            version TEXT NOT NULL,               -- KePrompt version  
            timestamp DATETIME NOT NULL,         -- Execution time
            tokens_in INTEGER NOT NULL,          -- Input tokens
            tokens_out INTEGER NOT NULL,         -- Output tokens
            estimated_costs REAL NOT NULL,       -- Total estimated cost
            elapsed_time REAL NOT NULL,          -- Execution duration in seconds
            
            -- Essential for cost engineering (always populated)
            model TEXT NOT NULL,                 -- AI model used
            provider TEXT NOT NULL,              -- AI provider
            cost_in REAL NOT NULL,              -- Input token cost
            cost_out REAL NOT NULL,             -- Output token cost
            session_id TEXT NOT NULL,           -- Session identifier
            call_id TEXT NOT NULL,              -- API call identifier
            
            -- Application-provided fields (NULL if not provided)
            project TEXT,                       -- Project/category (app-provided)
            parameters TEXT,                    -- JSON of parameters (captured from vm.vdict)
            
            -- Execution tracking (always populated)
            success BOOLEAN NOT NULL DEFAULT 1, -- Execution success
            error_message TEXT,                 -- Error details if failed
            
            -- Model configuration (captured when available)
            context_length INTEGER,             -- Context window used
            temperature REAL,                   -- Model temperature
            max_tokens INTEGER,                 -- Max tokens setting
            
            -- Operational metadata (auto-populated)
            hostname TEXT,                      -- Execution machine
            environment TEXT,                   -- Environment (dev/staging/prod)
            git_commit TEXT,                    -- Git commit hash
            execution_mode TEXT                 -- Mode (production/debug/log)
        )
        """
        
        self.conn.execute(create_sql)
        
        # Create indexes for efficient querying
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON cost_tracking(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_prompt_name ON cost_tracking(prompt_name)",
            "CREATE INDEX IF NOT EXISTS idx_model ON cost_tracking(model)",
            "CREATE INDEX IF NOT EXISTS idx_project ON cost_tracking(project)",
            "CREATE INDEX IF NOT EXISTS idx_session_id ON cost_tracking(session_id)"
        ]
        
        for index_sql in indexes:
            self.conn.execute(index_sql)
        
        self.conn.commit()
    
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
    
    def _get_environment(self) -> str:
        """Determine environment from environment variables."""
        env = os.getenv("ENVIRONMENT", "").lower()
        if env in ["dev", "development"]:
            return "development"
        elif env in ["stage", "staging"]:
            return "staging"
        elif env in ["prod", "production"]:
            return "production"
        else:
            return "development"  # Default
    
    def _get_project(self) -> str:
        """Get project from environment variable or current directory name."""
        # First try environment variable
        project = os.getenv("KEPROMPT_PROJECT")
        if project:
            return project
        
        # Fall back to current directory name
        try:
            return os.path.basename(os.getcwd())
        except:
            return "unknown"
    
    def track_execution(self,
                       prompt_name: str,
                       session_id: str,
                       call_id: str,
                       model: str,
                       provider: str,
                       tokens_in: int,
                       tokens_out: int,
                       cost_in: float,
                       cost_out: float,
                       elapsed_time: float,
                       execution_mode: str,
                       parameters: Optional[Dict[str, Any]] = None,
                       success: bool = True,
                       error_message: Optional[str] = None,
                       context_length: Optional[int] = None,
                       temperature: Optional[float] = None,
                       max_tokens: Optional[int] = None) -> None:
        """
        Track a prompt execution with cost and metadata.
        
        Args:
            prompt_name: Name of the prompt file (without path/extension)
            session_id: Unique session identifier
            call_id: Unique API call identifier
            model: AI model used
            provider: AI provider
            tokens_in: Input tokens consumed
            tokens_out: Output tokens generated
            cost_in: Input token cost
            cost_out: Output token cost
            elapsed_time: Execution duration in seconds
            execution_mode: Mode (production/debug/log)
            parameters: Parameters passed to prompt (optional)
            success: Whether execution succeeded
            error_message: Error details if failed
            context_length: Context window used
            temperature: Model temperature setting
            max_tokens: Max tokens setting
        """
        if not self.conn:
            return  # Database not available
        
        # Calculate total cost
        total_cost = cost_in + cost_out
        
        # Prepare parameters as JSON string
        parameters_json = None
        if parameters:
            try:
                parameters_json = json.dumps(parameters)
            except (TypeError, ValueError):
                parameters_json = str(parameters)
        
        # Collect metadata
        timestamp = datetime.now().isoformat()
        hostname = socket.gethostname()
        environment = self._get_environment()
        git_commit = self._get_git_commit()
        project = self._get_project()
        
        # Insert record
        insert_sql = """
        INSERT INTO cost_tracking (
            prompt_name, version, timestamp, tokens_in, tokens_out, estimated_costs, elapsed_time,
            model, provider, cost_in, cost_out, session_id, call_id,
            project, parameters, success, error_message,
            context_length, temperature, max_tokens,
            hostname, environment, git_commit, execution_mode
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        values = (
            prompt_name, __version__, timestamp, tokens_in, tokens_out, total_cost, elapsed_time,
            model, provider, cost_in, cost_out, session_id, call_id,
            project, parameters_json, success, error_message,
            context_length, temperature, max_tokens,
            hostname, environment, git_commit, execution_mode
        )
        
        try:
            self.conn.execute(insert_sql, values)
            self.conn.commit()
        except sqlite3.Error as e:
            # Log error but don't fail execution
            print(f"Warning: Cost tracking failed: {e}", file=os.sys.stderr)
    
    def get_session_costs(self, session_id: str) -> Dict[str, Any]:
        """
        Get cost summary for a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with cost summary
        """
        if not self.conn:
            return {}
        
        query = """
        SELECT 
            COUNT(*) as call_count,
            SUM(tokens_in) as total_tokens_in,
            SUM(tokens_out) as total_tokens_out,
            SUM(cost_in) as total_cost_in,
            SUM(cost_out) as total_cost_out,
            SUM(estimated_costs) as total_cost,
            AVG(elapsed_time) as avg_elapsed_time,
            MAX(timestamp) as last_call
        FROM cost_tracking 
        WHERE session_id = ?
        """
        
        cursor = self.conn.execute(query, (session_id,))
        row = cursor.fetchone()
        
        if row and row[0] > 0:  # call_count > 0
            return {
                "call_count": row[0],
                "total_tokens_in": row[1] or 0,
                "total_tokens_out": row[2] or 0,
                "total_cost_in": row[3] or 0.0,
                "total_cost_out": row[4] or 0.0,
                "total_cost": row[5] or 0.0,
                "avg_elapsed_time": row[6] or 0.0,
                "last_call": row[7]
            }
        
        return {}
    
    def get_recent_costs(self, limit: int = 10) -> list:
        """
        Get recent cost entries.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of recent cost entries
        """
        if not self.conn:
            return []
        
        query = """
        SELECT prompt_name, model, tokens_in, tokens_out, estimated_costs, timestamp
        FROM cost_tracking 
        ORDER BY timestamp DESC 
        LIMIT ?
        """
        
        cursor = self.conn.execute(query, (limit,))
        return cursor.fetchall()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Global cost tracker instance (initialized when needed)
_global_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Get global cost tracker instance."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = CostTracker()
    return _global_tracker


def track_prompt_execution(prompt_name: str,
                          session_id: str,
                          call_id: str,
                          model: str,
                          provider: str,
                          tokens_in: int,
                          tokens_out: int,
                          cost_in: float,
                          cost_out: float,
                          elapsed_time: float,
                          execution_mode: str,
                          **kwargs) -> None:
    """
    Convenience function to track prompt execution.
    
    This is the main entry point for cost tracking from the VM.
    """
    tracker = get_cost_tracker()
    tracker.track_execution(
        prompt_name=prompt_name,
        session_id=session_id,
        call_id=call_id,
        model=model,
        provider=provider,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_in=cost_in,
        cost_out=cost_out,
        elapsed_time=elapsed_time,
        execution_mode=execution_mode,
        **kwargs
    )
