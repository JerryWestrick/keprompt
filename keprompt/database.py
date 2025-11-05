"""
Database models and connection management for KePrompt.

Uses Peewee ORM with support for SQLite, PostgreSQL, and MySQL via SQLAlchemy-style URLs.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from peewee import *

from .chat_viewer import chatViewerApp
from .config import get_config
from .version import __version__


# Global database instance
database_proxy = DatabaseProxy()


class BaseModel(Model):
    """Base model with common functionality."""
    
    class Meta:
        database = database_proxy


class Chat(BaseModel):
    """Master table for chats."""
    
    # Primary key
    chat_id = CharField(primary_key=True, max_length=8)
    
    # chat identification
    created_timestamp = DateTimeField(default=datetime.now)
    
    # Prompt metadata (from .prompt statement)
    prompt_name = CharField(max_length=255, null=True)
    prompt_version = CharField(max_length=50, null=True)
    prompt_filename = CharField(max_length=255, null=True)
    
    # chat data (JSON blobs)
    messages_json = TextField()
    vm_state_json = TextField(null=True)
    variables_json = TextField(null=True)
    statements_json = TextField(null=True)
    
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
        table_name = 'chats'
        indexes = (
            (('created_timestamp',), False),
            (('prompt_filename',), False),
        )


class ServerRegistry(BaseModel):
    """Global registry for running keprompt HTTP servers."""
    
    # Primary key
    directory = CharField(primary_key=True, max_length=512)
    
    # Server information
    port = IntegerField()
    pid = IntegerField()
    status = CharField(max_length=20)  # 'running' or 'died'
    
    # Timestamps
    started_at = DateTimeField(default=datetime.now)
    died_at = DateTimeField(null=True)
    
    # Configuration
    web_gui_enabled = BooleanField(default=False)
    
    class Meta:
        table_name = 'server_registry'
        indexes = (
            (('status',), False),
            (('started_at',), False),
        )


class CostTracking(BaseModel):
    """Child table for individual API call costs."""
    
    # Composite primary key
    chat_id = CharField(max_length=8)
    msg_no = IntegerField()
    
    # Note: No foreign key constraint - cost tracking works independently of chats
    
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
        primary_key = CompositeKey('chat_id', 'msg_no')
        indexes = (
            (('timestamp',), False),
            (('model',), False),
            (('chat_id',), False),
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
    """Initialize database connection and create tables, migrating legacy schema if needed."""
    if url is None:
        config = get_config()
        url = config.get_database_url()
    
    # Create database connection
    db = create_database_from_url(url)
    
    # Initialize the proxy
    database_proxy.initialize(db)
    
    # Legacy migration removed; assuming fresh chat schema
    
    # Create tables if they don't exist
    with db:
        db.create_tables([Chat, ServerRegistry, CostTracking], safe=True)
    
    return db


def get_database() -> Database:
    """Get the current database connection."""
    if database_proxy.obj is None:
        initialize_database()
    return database_proxy.obj


class DatabaseManager:
    """High-level database operations."""
    
    def __init__(self, args: argparse.Namespace = None):
        self.args = args
        self.db = get_database()
    
    def save_chat(self, chat_id: str, chat_name: str,
                  messages_json: str, vm_state_json: str = None,
                  variables_json: str = None, statements_json: str = None,
                  **metadata) -> Chat:
        """Save or update a chat."""
        
        with self.db.atomic():
            chat, created = Chat.get_or_create(
                chat_id=chat_id,
                defaults={
                    'messages_json': messages_json,
                    'vm_state_json': vm_state_json,
                    'variables_json': variables_json,
                    'statements_json': statements_json,
                    **metadata
                }
            )
            
            if not created:
                # Update existing chat
                chat.messages_json = messages_json
                chat.vm_state_json = vm_state_json
                chat.variables_json = variables_json
                chat.statements_json = statements_json
                for key, value in metadata.items():
                    setattr(chat, key, value)
                chat.save()
            
            return chat
    
    def save_cost_tracking(self, chat_id: str, msg_no: int, **cost_data) -> CostTracking:
        """Save cost tracking data."""
        with self.db.atomic():
            cost_record, created = CostTracking.get_or_create(
                chat_id=chat_id,
                msg_no=msg_no,
                defaults=cost_data
            )
            
            if not created:
                # Update existing record
                for key, value in cost_data.items():
                    setattr(cost_record, key, value)
                cost_record.save()
            
            return cost_record
    
    def get_chat(self, chat_id: str) -> Optional[Chat]:
        """Get chat by chat ID."""
        try:
            return Chat.get(Chat.chat_id == chat_id)
        except Chat.DoesNotExist:
            return None
    
    def get_chat_with_costs(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """Get chat with all related cost data."""
        chat = self.get_chat(chat_id)
        if not chat:
            return None
        
        costs = list(CostTracking.select().where(CostTracking.chat_id == chat_id).order_by(CostTracking.msg_no))
        
        return {
            'chat': chat,
            'costs': costs,
            'messages': json.loads(chat.messages_json) if chat.messages_json else [],
            'vm_state': json.loads(chat.vm_state_json) if chat.vm_state_json else {},
            'variables': json.loads(chat.variables_json) if chat.variables_json else {},
            'statements': json.loads(chat.statements_json) if chat.statements_json else []
        }
    
    def list_chats(self, limit: int = 100, offset: int = 0) -> List[Chat]:
        """List chats ordered by creation time."""
        query = Chat.select().order_by(Chat.created_timestamp.desc())
        query = query.limit(limit)
        query = query.offset(offset)
        return list(query)
    
    def delete_chat(self, chat_id: str) -> bool:
        """Delete chat and all related cost data."""
        with self.db.atomic():
            try:
                chat = Chat.get(Chat.chat_id == chat_id)
                # Delete related cost records (CASCADE should handle this, but be explicit)
                CostTracking.delete().where(CostTracking.chat_id == chat_id).execute()
                chat.delete_instance()
                return True
            except Chat.DoesNotExist:
                return False
    
    def cleanup_old_chats(self, max_days: int = None, max_count: int = None, max_size_gb: float = None) -> Dict[str, int]:
        """Clean up old chats based on criteria."""
        deleted_chats = 0
        deleted_costs = 0
        
        with self.db.atomic():
            # Age-based cleanup
            if max_days:
                cutoff_date = datetime.now() - timedelta(days=max_days)
                old_chats = Chat.select().where(Chat.created_timestamp < cutoff_date)
                
                for conv in old_chats:
                    deleted_costs += CostTracking.delete().where(CostTracking.chat_id == conv.chat_id).execute()
                    deleted_chats += 1
                
                Chat.delete().where(Chat.created_timestamp < cutoff_date).execute()
            
            # Count-based cleanup
            if max_count:
                total_count = Chat.select().count()
                if total_count > max_count:
                    excess_chats = Chat.select().order_by(Chat.created_timestamp.asc()).limit(total_count - max_count)
                    
                    for conv in excess_chats:
                        deleted_costs += CostTracking.delete().where(CostTracking.chat_id == conv.chat_id).execute()
                        conv.delete_instance()
                        deleted_chats += 1
        
        return {
            'deleted_chats': deleted_chats,
            'deleted_costs': deleted_costs
        }
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        chat_count = Chat.select().count()
        cost_count = CostTracking.select().count()
        
        # Get database file size for SQLite
        db_size = 0
        if isinstance(self.db, SqliteDatabase) and self.db.database != ':memory:':
            try:
                db_size = os.path.getsize(self.db.database)
            except (OSError, AttributeError):
                pass
        
        return {
            'chat_count': chat_count,
            'cost_records': cost_count,
            'database_size_bytes': db_size,
            'database_size_mb': round(db_size / (1024 * 1024), 2) if db_size else 0
        }

    def execute(self):

        cmd = self.args.database_command

        # if getattr(self.args, "pretty", False):
        #     table = Table(title="Available Functions")
        #     table.add_column("Name", style="cyan", no_wrap=True)
        #     table.add_column("Description/Parameters", style="green")
        #
        #     for tool in DefinedToolsArray:
        #         function = tool['function']
        #         name = function['name']
        #         description = function['description']
        #
        #         table.add_row(name, description,)
        #         for k, v in function.get('parameters', {}).get('properties', {}).items():
        #             table.add_row("", f"[bold blue]{k:10}[/]: {v.get('description', '')}")
        #
        #         table.add_row("", "")
        #
        #     return table

        # default: text
        return {"success": True, "data": {'cmd': cmd}, "timestamp": datetime.now().isoformat()}





# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
