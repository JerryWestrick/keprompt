"""
Centralized output formatting for keprompt CLI.
Handles both JSON serialization and Rich table formatting.
"""
import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from rich.table import Table
from rich.markdown import Markdown


class OutputFormatter:
    """Centralized formatter that converts JSON to Rich tables"""
    
    # Provider color mapping
    PROVIDER_COLORS = {
        'openrouter': 'yellow',
        'openai': 'green',
        'anthropic': 'magenta',
        'gemini': 'red',
        'google': 'red',
        'mistral': 'bright_yellow',
        'xai': 'white',
        'deepseek': 'blue',
    }
    
    # Role color mapping for chat messages
    ROLE_COLORS = {
        'system': 'cyan',
        'user': 'green',
        'assistant': 'yellow',
        'tool': 'cyan',
        'tool_result': 'cyan'
    }
    
    @classmethod
    def format(cls, data: Any, format_type: str = "pretty", response_type: Optional[str] = None, title: Optional[str] = None) -> Any:
        """
        Format data for output - handles both JSON and pretty display.
        
        Args:
            data: Data to format
            format_type: "json" for JSON string, "pretty" for Rich tables (default)
            response_type: Optional hint for custom formatting (deprecated, use object_type in data)
            title: Optional table title
            
        Returns:
            JSON string if format_type=="json", Rich Table if format_type=="pretty"
        """
        if format_type == "json":
            return cls._format_json(data)
        else:
            return cls._format_pretty(data, response_type, title)
    
    @classmethod
    def _format_json(cls, data: Any) -> str:
        """
        Format data as JSON string with proper serialization.
        Handles Peewee models, datetime objects, Decimals, etc.
        """
        def serialize(obj):
            """Custom serializer for non-JSON types"""
            # Handle Peewee models
            if hasattr(obj, '__data__'):
                return obj.__data__
            # Handle datetime
            elif isinstance(obj, datetime):
                return obj.isoformat()
            # Handle Decimal
            elif isinstance(obj, Decimal):
                return float(obj)
            # Handle Path objects
            elif hasattr(obj, '__class__') and 'Path' in obj.__class__.__name__:
                return str(obj)
            # Handle other objects with __dict__
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            # Fallback to string
            else:
                return str(obj)
        
        return json.dumps(data, indent=2, default=serialize)
    
    @classmethod
    def _format_pretty(cls, data: Any, response_type: Optional[str] = None, title: Optional[str] = None) -> Any:
        """
        Format data as Rich table for pretty display.
        
        Args:
            data: JSON/dict data to format
            response_type: Optional hint for custom formatting (deprecated, use object_type in data)
            title: Optional table title
            
        Returns:
            Rich Table object or original data if not formattable
        """
        # Extract object_type and view_format from data if present
        object_type = None
        view_format = None
        if isinstance(data, dict):
            object_type = data.get("object_type") or response_type
            view_format = data.get("_view_format", "full")
        else:
            object_type = response_type
        
        # Handle chat detail with view format options
        if view_format and view_format != "full" and isinstance(data, dict) and "messages" in data:
            return cls._format_chat_detail(data, view_format, title)
        
        # Handle special object types with custom formatting
        if object_type == "provider_list":
            return cls._format_provider_list(data, title)
        elif object_type == "chat_conversation":
            return cls._format_chat_conversation(data, title)
        
        # Generic auto-formatter for standard cases
        return cls._auto_format(data, title)
    
    @classmethod
    def _format_provider_list(cls, data: Dict, title: Optional[str] = None) -> Table:
        """Format provider list with custom color coding"""
        provider_list = data.get("data", [])
        
        table = Table(title=title or "Available Providers")
        table.add_column("Provider", style="cyan", no_wrap=True)
        table.add_column("Model Count", style="green", justify="right")
        
        for provider in provider_list:
            provider_name = provider["name"]
            color = cls.PROVIDER_COLORS.get(provider_name.lower(), 'cyan')
            colored_name = f"[{color}]{provider_name}[/{color}]"
            table.add_row(colored_name, str(provider["models_count"]))
        
        return table
    
    @classmethod
    def _format_chat_detail(cls, data: Dict, view_format: str, title: Optional[str] = None) -> Any:
        """
        Format chat detail with different view formats.
        
        Args:
            data: Chat data including messages, costs, etc.
            view_format: View format (messages, statements, summary, raw)
            title: Optional title
        """
        # Extract chat_id from either the chat object or direct field
        chat = data.get("chat")
        if hasattr(chat, 'chat_id'):
            chat_id = chat.chat_id
        elif isinstance(chat, str):
            chat_id = chat
        else:
            chat_id = ""
        
        # Handle format aliases
        format_aliases = {
            'message': 'messages',
            'msgs': 'messages',
            'msg': 'messages',
            'statement': 'statements',
            'stmts': 'statements',
            'stmt': 'statements',
            'sum': 'summary',
            'json': 'raw',
        }
        view_format = format_aliases.get(view_format, view_format)
        
        if view_format == "statements":
            # Show statement source code
            return cls._format_chat_statements(data, title)
        elif view_format == "messages":
            # Show only the conversation
            messages = data.get("messages", [])
            table = Table(title=title or f"Messages - {chat_id}")
            table.add_column("Role", style="cyan", no_wrap=True)
            table.add_column("Model", style="yellow", no_wrap=True)
            table.add_column("Message", style="green")
            
            for msg in messages:
                role = msg.get("role", "")
                
                # Get model info if available (for assistant messages)
                model_display = ""
                if role == "assistant" and msg.get("model_name"):
                    model_name = msg["model_name"]
                    short_model = model_name.split('/')[-1] if '/' in model_name else model_name
                    provider = msg.get('provider', '').lower()
                    color = cls.PROVIDER_COLORS.get(provider, 'yellow')
                    model_display = f"[{color}]{short_model}[/{color}]"
                
                # Build message text
                txt = ''
                for part in msg.get("content", []):
                    part_type = part.get("type", "")
                    
                    if part_type == "text":
                        txt += f"{part.get('text', '')}\n"
                    elif part_type == "tool":
                        args_str = ', '.join(f"{k}={v}" for k, v in part.get('arguments', {}).items())
                        txt += f"**Call** `{part.get('name', '')}({args_str})` [id={part.get('id', '')}]\n"
                    elif part_type == "tool_result":
                        result = str(part.get('content', ''))
                        result_preview = result[:200] + '...' if len(result) > 200 else result
                        txt += f"**Result** `{part.get('name', '')}()`: {result_preview} [id={part.get('tool_use_id', '')}]\n"
                
                if txt:
                    # Colorize role
                    role_color = cls.ROLE_COLORS.get(role, 'white')
                    colored_role = f"[{role_color}]{role}[/{role_color}]"
                    md = Markdown(txt[:-1])  # Remove trailing newline
                    table.add_row(colored_role, model_display, md)
            
            return table
        
        elif view_format == "summary":
            # Show only metadata (costs, tokens, etc.)
            costs = data.get("costs", [])
            vm_state = data.get("vm_state", {})
            
            table = Table(title=title or f"Chat Summary - {chat_id}")
            table.add_column("Metric", style="cyan", no_wrap=True)
            table.add_column("Value", style="green")
            
            # Add summary metrics
            total_cost_in = sum(float(c.get('cost_in', 0)) for c in costs)
            total_cost_out = sum(float(c.get('cost_out', 0)) for c in costs)
            total_tokens_in = sum(c.get('tokens_in', 0) for c in costs)
            total_tokens_out = sum(c.get('tokens_out', 0) for c in costs)
            total_time = sum(float(c.get('elapsed_time', 0)) for c in costs)
            
            table.add_row("Chat ID", chat_id)
            table.add_row("Prompt", f"{vm_state.get('prompt_name', 'N/A')} v{vm_state.get('prompt_version', 'N/A')}")
            table.add_row("Model", vm_state.get('model_name', 'N/A'))
            table.add_row("Provider", vm_state.get('provider', 'N/A'))
            table.add_row("API Calls", str(len(costs)))
            table.add_row("Total Tokens In", f"{total_tokens_in:,}")
            table.add_row("Total Tokens Out", f"{total_tokens_out:,}")
            table.add_row("Cost In", f"${total_cost_in:.6f}")
            table.add_row("Cost Out", f"${total_cost_out:.6f}")
            table.add_row("Total Cost", f"${total_cost_in + total_cost_out:.6f}")
            table.add_row("Total Time", f"{total_time:.2f}s")
            table.add_row("Messages", str(len(data.get('messages', []))))
            
            return table
        
        elif view_format == "raw":
            # Show as JSON Panel
            from rich.panel import Panel
            from rich.syntax import Syntax
            import json
            
            json_str = json.dumps(data, indent=2, default=str)
            syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
            return Panel(syntax, title=title or f"Chat Detail (Raw) - {chat_id}", border_style="cyan")
        
        # Default to full view (same as raw for now)
        return cls._auto_format(data, title)
    
    @classmethod
    def _format_chat_statements(cls, data: Dict, title: Optional[str] = None) -> Table:
        """Format chat statements (source code view)"""
        statements = data.get("statements", [])
        vm_state = data.get("vm_state", {})
        
        # Extract chat_id from either the chat object or direct field
        chat = data.get("chat")
        if hasattr(chat, 'chat_id'):
            chat_id = chat.chat_id
        elif isinstance(chat, str):
            chat_id = chat
        else:
            chat_id = ""
        
        current_ip = vm_state.get("ip", 0) if isinstance(vm_state, dict) else 0
        
        table = Table(title=title or f"Statements (Source Code) - {chat_id}")
        table.add_column("#", style="cyan", justify="right", width=4)
        table.add_column("Statement", style="yellow", no_wrap=True, width=12)
        table.add_column("Value", style="green")
        
        for stmt in statements:
            stmt_no = stmt.get('msg_no', 0)
            keyword = stmt.get('keyword', '')
            value = stmt.get('value', '')
            
            # Truncate long values
            if len(value) > 80:
                value = value[:77] + '...'
            
            # Highlight current IP
            if stmt_no == current_ip:
                num_display = f"[bold white]→{stmt_no}[/bold white]"
            else:
                num_display = str(stmt_no)
            
            table.add_row(num_display, keyword, value)
        
        # Add footer with current IP
        table.caption = f"Current IP: {current_ip}"
        
        return table
    
    @classmethod
    def _format_chat_conversation(cls, data: Dict, title: Optional[str] = None) -> Table:
        """Format chat conversation with Markdown and custom styling"""
        messages = data.get("messages", [])
        chat_id = data.get("chat_id", "")
        prompt_name = data.get("prompt_name", "")
        prompt_version = data.get("prompt_version", "")
        
        default_title = f"Conversation {chat_id}[{prompt_name}:{prompt_version}]"
        table = Table(title=title or default_title)
        table.add_column("Role", style="cyan", no_wrap=True)
        table.add_column("Model", style="yellow", no_wrap=True)
        table.add_column("Message", style="green")
        
        for msg in messages:
            role = msg.get("role", "")
            
            # Get model info if available (for assistant messages)
            model_display = ""
            if role == "assistant" and msg.get("model_name"):
                model_name = msg["model_name"]
                short_model = model_name.split('/')[-1] if '/' in model_name else model_name
                provider = msg.get('provider', '').lower()
                color = cls.PROVIDER_COLORS.get(provider, 'yellow')
                model_display = f"[{color}]{short_model}[/{color}]"
            
            # Build message text
            txt = ''
            for part in msg.get("content", []):
                part_type = part.get("type", "")
                
                if part_type == "text":
                    txt += f"{part.get('text', '')}\n"
                elif part_type == "tool":
                    args_str = ', '.join(f"{k}={v}" for k, v in part.get('arguments', {}).items())
                    txt += f"**Call** `{part.get('name', '')}({args_str})` [id={part.get('id', '')}]\n"
                elif part_type == "tool_result":
                    result = str(part.get('content', ''))
                    result_preview = result[:200] + '...' if len(result) > 200 else result
                    txt += f"**Result** `{part.get('name', '')}()`: {result_preview} [id={part.get('tool_use_id', '')}]\n"
            
            if txt:
                # Colorize role
                role_color = cls.ROLE_COLORS.get(role, 'white')
                colored_role = f"[{role_color}]{role}[/{role_color}]"
                md = Markdown(txt[:-1])  # Remove trailing newline
                table.add_row(colored_role, model_display, md)
        
        return table
    
    @classmethod
    def _auto_format(cls, data: Any, title: Optional[str] = None) -> Any:
        """
        Generic auto-formatter for standard JSON structures.
        Handles lists of dicts and single dicts automatically.
        """
        # Extract actual data if wrapped in success envelope
        if isinstance(data, dict) and "data" in data:
            actual_data = data["data"]
        else:
            actual_data = data
        
        # Pattern 1: List of dicts with same keys → multi-column table
        if isinstance(actual_data, list) and actual_data and isinstance(actual_data[0], dict):
            keys = list(actual_data[0].keys())
            table = Table(title=title or "Results")
            
            for key in keys:
                # Format column names: snake_case → Title Case
                col_name = key.replace('_', ' ').title()
                table.add_column(col_name)
            
            for row in actual_data:
                table.add_row(*[str(row.get(k, '')) for k in keys])
            
            return table
        
        # Pattern 2: Single dict → Pretty JSON Panel (more readable for nested structures)
        if isinstance(actual_data, dict):
            from rich.panel import Panel
            from rich.syntax import Syntax
            import json
            
            # Format as pretty JSON with syntax highlighting
            json_str = json.dumps(actual_data, indent=2, default=str)
            syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
            return Panel(syntax, title=title or "Details", border_style="cyan")
            
            # OLD: Table format (kept as reference, can restore if needed)
            # table = Table(title=title or "Details")
            # table.add_column("Field", style="cyan", no_wrap=True)
            # table.add_column("Value", style="green")
            # for k, v in actual_data.items():
            #     if isinstance(v, (dict, list)):
            #         value_str = json.dumps(v, indent=2)
            #     else:
            #         value_str = str(v)
            #     table.add_row(k, value_str)
            # return table
        
        # Fallback: return as-is (string, number, etc.)
        return actual_data
