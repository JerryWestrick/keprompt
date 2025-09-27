"""
Database models and connection management for KePrompt.

Uses Peewee ORM with support for SQLite, PostgreSQL, and MySQL via SQLAlchemy-style URLs.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from peewee import *

from .config import get_config
from .version import __version__


# Global database instance
database_proxy = DatabaseProxy()


class BaseModel(Model):
    """Base model with common functionality."""
    
    class Meta:
        database = database_proxy


class Session(BaseModel):
    """Master table for sessions."""
    
    # Primary key
    session_id = CharField(primary_key=True, max_length=8)
    
    # session identification
    created_timestamp = DateTimeField(default=datetime.now)
    
    # Prompt metadata (from .prompt statement)
    prompt_name = CharField(max_length=255, null=True)
    prompt_version = CharField(max_length=50, null=True)
    prompt_filename = CharField(max_length=255, null=True)
    
    # session data (JSON blobs)
    messages_json = TextField()
    vm_state_json = TextField(null=True)
    variables_json = TextField(null=True)
    
    # Execution metadata
    keprompt_version = CharField(max_length=50, default=__version__)
    hostname = CharField(max_length=255, null=True)
    git_commit = CharField(max_length=40, null=True)
    
    # Summary stats (derived from cost_tracking)
    total_api_calls = IntegerField(default=0)
    total_tokens_in = IntegerField(default=0)
    total_tokens_out = IntegerField(default=0)
    total_cost = DecimalField(max_digits=10, decimal_places=6, default=0.0)
    
    class Meta:
        table_name = 'sessions'
        indexes = (
            (('created_timestamp',), False),
            (('prompt_filename',), False),
        )


class CostTracking(BaseModel):
    """Child table for individual API call costs."""
    
    # Composite primary key
    session_id = CharField(max_length=8)
    msg_no = IntegerField()
    
    # Note: No foreign key constraint - cost tracking works independently of sessions
    
    # API call identification
    call_id = CharField(max_length=50)
    timestamp = DateTimeField(default=datetime.now)
    
    # Cost and token data
    tokens_in = IntegerField()
    tokens_out = IntegerField()
    cost_in = DecimalField(max_digits=10, decimal_places=6)
    cost_out = DecimalField(max_digits=10, decimal_places=6)
    estimated_costs = DecimalField(max_digits=10, decimal_places=6)
    elapsed_time = DecimalField(max_digits=8, decimal_places=3)
    
    # Model information
    model = CharField(max_length=100)
    provider = CharField(max_length=50)
    
    # Execution status
    success = BooleanField(default=True)
    error_message = TextField(null=True)
    
    # Model configuration
    temperature = DecimalField(max_digits=3, decimal_places=2, null=True)
    max_tokens = IntegerField(null=True)
    context_length = IntegerField(null=True)
    
    # Additional metadata from original cost_tracker
    prompt_semantic_name = CharField(max_length=255, null=True)
    prompt_version_tracking = CharField(max_length=50, null=True)
    expected_params = TextField(null=True)  # JSON
    execution_mode = CharField(max_length=20, default='production')
    parameters = TextField(null=True)  # JSON
    environment = CharField(max_length=20, null=True)
    
    class Meta:
        table_name = 'cost_tracking'
        primary_key = CompositeKey('session_id', 'msg_no')
        indexes = (
            (('timestamp',), False),
            (('model',), False),
            (('session_id',), False),
        )


def create_database_from_url(url: str) -> Database:
    """Create database connection from SQLAlchemy-style URL."""
    parsed = urlparse(url)
    
    if parsed.scheme == 'sqlite':
        # sqlite:///path/to/db.db or sqlite:///:memory:
        if parsed.path == '/:memory:':
            db_path = ':memory:'
        else:
            db_path = parsed.path[1:]  # Remove leading /
            # Ensure directory exists
            db_dir = Path(db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
        return SqliteDatabase(db_path)
        
    elif parsed.scheme == 'postgresql':
        # postgresql://user:pass@host:port/dbname
        return PostgresqlDatabase(
            parsed.path[1:],  # database name (remove leading /)
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname or 'localhost',
            port=parsed.port or 5432
        )
        
    elif parsed.scheme == 'mysql':
        # mysql://user:pass@host:port/dbname
        return MySQLDatabase(
            parsed.path[1:],  # database name (remove leading /)
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname or 'localhost',
            port=parsed.port or 3306
        )
    
    else:
        raise ValueError(f"Unsupported database URL scheme: {parsed.scheme}")


def initialize_database(url: Optional[str] = None) -> Database:
    """Initialize database connection and create tables."""
    if url is None:
        config = get_config()
        url = config.get_database_url()
    
    # Create database connection
    db = create_database_from_url(url)
    
    # Initialize the proxy
    database_proxy.initialize(db)
    
    # Create tables if they don't exist
    with db:
        db.create_tables([Session, CostTracking], safe=True)
    
    return db


def get_database() -> Database:
    """Get the current database connection."""
    if database_proxy.obj is None:
        initialize_database()
    return database_proxy.obj


class DatabaseManager:
    """High-level database operations."""
    
    def __init__(self):
        self.db = get_database()
    
    def save_session(self, session_id: str,session_name: str,
                     messages_json: str, vm_state_json: str = None,
                     variables_json: str = None, **metadata) -> Session:
        """Save or update a session."""
        
        with self.db.atomic():
            session, created = Session.get_or_create(
                session_id=session_id,
                defaults={
                    'messages_json': messages_json,
                    'vm_state_json': vm_state_json,
                    'variables_json': variables_json,
                    **metadata
                }
            )
            
            if not created:
                # Update existing session
                session.messages_json = messages_json
                session.vm_state_json = vm_state_json
                session.variables_json = variables_json
                for key, value in metadata.items():
                    setattr(session, key, value)
                session.save()
            
            return session
    
    def save_cost_tracking(self, session_id: str, msg_no: int, **cost_data) -> CostTracking:
        """Save cost tracking data."""
        with self.db.atomic():
            cost_record, created = CostTracking.get_or_create(
                session_id=session_id,
                msg_no=msg_no,
                defaults=cost_data
            )
            
            if not created:
                # Update existing record
                for key, value in cost_data.items():
                    setattr(cost_record, key, value)
                cost_record.save()
            
            return cost_record
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by session ID."""
        try:
            return Session.get(Session.session_id == session_id)
        except Session.DoesNotExist:
            return None
    
    def get_session_with_costs(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session with all related cost data."""
        session = self.get_session(session_id)
        if not session:
            return None
        
        costs = list(CostTracking.select().where(CostTracking.session_id == session_id).order_by(CostTracking.msg_no))
        
        return {
            'session': session,
            'costs': costs,
            'messages': json.loads(session.messages_json) if session.messages_json else [],
            'vm_state': json.loads(session.vm_state_json) if session.vm_state_json else {},
            'variables': json.loads(session.variables_json) if session.variables_json else {}
        }
    
    def list_sessions(self, limit: int = 100, offset: int = 0) -> List[Session]:
        """List sessions ordered by creation time."""
        return list(Session.select().order_by(Session.created_timestamp.desc()).limit(limit).offset(offset))
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session and all related cost data."""
        with self.db.atomic():
            try:
                session = Session.get(Session.session_id == session_id)
                # Delete related cost records (CASCADE should handle this, but be explicit)
                CostTracking.delete().where(CostTracking.session_id == session_id).execute()
                session.delete_instance()
                return True
            except Session.DoesNotExist:
                return False
    
    def cleanup_old_sessions(self, max_days: int = None, max_count: int = None, max_size_gb: float = None) -> Dict[str, int]:
        """Clean up old sessions based on criteria."""
        deleted_sessions = 0
        deleted_costs = 0
        
        with self.db.atomic():
            # Age-based cleanup
            if max_days:
                cutoff_date = datetime.now() - timedelta(days=max_days)
                old_sessions = Session.select().where(Session.created_timestamp < cutoff_date)
                
                for conv in old_sessions:
                    deleted_costs += CostTracking.delete().where(CostTracking.session_id == conv.session_id).execute()
                    deleted_sessions += 1
                
                Session.delete().where(Session.created_timestamp < cutoff_date).execute()
            
            # Count-based cleanup
            if max_count:
                total_count = Session.select().count()
                if total_count > max_count:
                    excess_sessions = Session.select().order_by(Session.created_timestamp.asc()).limit(total_count - max_count)
                    
                    for conv in excess_sessions:
                        deleted_costs += CostTracking.delete().where(CostTracking.session_id == conv.session_id).execute()
                        conv.delete_instance()
                        deleted_sessions += 1
        
        return {
            'deleted_sessions': deleted_sessions,
            'deleted_costs': deleted_costs
        }
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        session_count = Session.select().count()
        cost_count = CostTracking.select().count()
        
        # Get database file size for SQLite
        db_size = 0
        if isinstance(self.db, SqliteDatabase) and self.db.database != ':memory:':
            try:
                db_size = os.path.getsize(self.db.database)
            except (OSError, AttributeError):
                pass
        
        return {
            'session_count': session_count,
            'cost_records': cost_count,
            'database_size_bytes': db_size,
            'database_size_mb': round(db_size / (1024 * 1024), 2) if db_size else 0
        }


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
