"""
Textual-based chat viewer for keprompt debug chats.
Provides a collapsible, interactive view of chat messages and function calls.
"""

import sys  # Add this import at the top of the file
import json
import asyncio
import warnings
from pathlib import Path
from typing import List

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Label, ListView, ListItem, Tree, Static, Input, Button, DataTable
from textual.binding import Binding
from textual.screen import Screen, ModalScreen
from rich.markdown import Markdown

# Suppress ResourceWarning for unclosed client chats
warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*client_chat")


class ChatViewer(Screen):
    """Main chat viewing screen"""
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "back", "Back"),
        Binding("f5", "copy_text", "Copy Text"),
        Binding("f6", "select_all", "Select All"),
        Binding("c", "copy_text", "Copy"),
        Binding("a", "select_all", "Select All"),
        Binding("s", "sort_menu", "Sort"),
        Binding("m", "toggle_markdown", "Toggle Markdown"),
    ]
    
    def __init__(self, initial_chat_name: str = ""):
        super().__init__()
        self.initial_chat_name = initial_chat_name
        self.selected_chat = initial_chat_name or "No chat selected"
        self.chats = self._get_all_chats()
        self.chat_data = None
        self.top_container_collapsed = False
        self.markdown_mode = False  # Toggle state for markdown rendering
        self.current_message_content = ""  # Store current message content for re-rendering
        self.current_message_role = ""  # Store current message role
        
    def _get_all_chats(self) -> List[dict]:
        """Get list of all available chats from database"""
        try:
            from .chat_manager import ChatManager
            chat_manager = ChatManager()
            # Remove arbitrary limit or make it configurable
            chats = chat_manager.list_chats(limit=10000)
        
        
            return chats
        except ImportError as e:
            print(f"ERROR: viewer._get_all_chats - Import failed: {e}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"ERROR: viewer._get_all_chats - Unexpected error: {e}", file=sys.stderr)
            return []
    
    def _load_chat(self, chat_id: str) -> dict:
        """Load chat data from database"""
        try:
            from .chat_manager import ChatManager
            chat_manager = ChatManager()
            data = chat_manager.get_chat(chat_id)
            
            if not data:
                return {}
            
            # Convert database format to the expected format
            chat = data['chat']
            return {
                'messages': data['messages'],
                'vm_state': json.loads(chat.vm_state_json) if chat.vm_state_json else {},
                'variables': data['variables']
            }
        except Exception:
            return {}
    
    def _truncate_text(self, text: str, max_length: int = 60) -> str:
        """Truncate text for display in tree"""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    def _get_role_icon(self, role: str) -> str:
        """Get icon for message role"""
        icons = {
            'system': '🔧',
            'user': '👤',
            'assistant': '🤖'
        }
        return icons.get(role, '💬')
    
    def _parse_assistant_message(self, content: str) -> str:
        """Parse assistant message for special analysis/response formatting"""
        # Check if message contains the special formatting pattern
        if '<|end|><|start|>assistantfinal' in content:
            # Split the content
            parts = content.split('<|end|><|start|>assistantfinal')
            if len(parts) == 2:
                analysis_part = parts[0].strip()
                response_part = parts[1].strip()
                
                # Remove 'analysis' prefix if it exists at the beginning
                if analysis_part.lower().startswith('analysis'):
                    analysis_part = analysis_part[8:].strip()  # Remove 'analysis' and any whitespace
                
                # Format with colors and section headers (white headers, colored content)
                formatted_content = f"[white]--- Analysis ---[/white]\n[blue]{analysis_part}[/blue]\n\n[white]--- Response ---[/white]\n[green]{response_part}[/green]"
                return formatted_content
        
        # Return original content if no special formatting detected
        return content
    
    def _extract_plain_text(self, rich_text: str) -> str:
        """Extract plain text from Rich markup by removing color tags"""
        import re
        # Remove Rich markup tags like [blue], [/blue], [green], [/green]
        plain_text = re.sub(r'\[/?[a-zA-Z_][a-zA-Z0-9_]*\]', '', rich_text)
        return plain_text
    
    def _format_as_table(self, data: dict, title: str = "Variable") -> str:
        """Format dictionary data as a table with Unicode box drawing characters"""
        if not data:
            return "No data available"
        
        # Calculate the maximum width for the variable column
        max_var_width = max(len(str(key)) for key in data.keys())
        max_var_width = max(max_var_width, len(title))  # At least as wide as the title
        
        # Unicode box drawing characters
        top_left = "┌"
        top_right = "┐"
        bottom_left = "└"
        bottom_right = "┘"
        horizontal = "─"
        vertical = "│"
        cross = "┼"
        top_tee = "┬"
        bottom_tee = "┴"
        left_tee = "├"
        right_tee = "┤"
        
        # Create table header
        header_line = top_left + horizontal * (max_var_width + 2) + top_tee + horizontal * 61 + top_right
        header_row = f"{vertical} [cyan]{title:<{max_var_width}}[/cyan] {vertical} [bold]Value[/bold]"
        separator_line = left_tee + horizontal * (max_var_width + 2) + cross + horizontal * 61 + right_tee
        
        # Create table rows
        rows = []
        for key, value in data.items():
            # Truncate very long values for display
            value_str = str(value)
            if len(value_str) > 57:  # Leave room for padding
                value_str = value_str[:54] + "..."
            
            row = f"{vertical} [cyan]{str(key):<{max_var_width}}[/cyan] {vertical} {value_str}"
            rows.append(row)
        
        # Create bottom line
        bottom_line = bottom_left + horizontal * (max_var_width + 2) + bottom_tee + horizontal * 61 + bottom_right
        
        # Combine all parts
        table_parts = [header_line, header_row, separator_line] + rows + [bottom_line]
        return "\n".join(table_parts)
    
    def _update_message_display(self, content: str, role: str) -> None:
        """Update the message display with current content and role, respecting markdown mode"""
        detail_widget = self.query_one("#message-detail", Static)
        
        if not content:
            detail_widget.update("[Empty message]")
            return
        
        if self.markdown_mode:
            # Render as markdown
            try:
                markdown_content = Markdown(content)
                detail_widget.update(markdown_content)
            except Exception:
                # Fallback to plain text if markdown rendering fails
                detail_widget.update(content)
        else:
            # Text mode - apply existing formatting logic
            if role == 'assistant':
                # Apply special parsing for assistant messages
                formatted_content = self._parse_assistant_message(content)
                detail_widget.update(formatted_content)
            else:
                # Regular display for other roles
                detail_widget.update(content)
        
    def compose(self) -> ComposeResult:
        """Create the UI layout"""
        yield Header()
        
        with Container(id="main-container"):
            with Vertical():
                # Top container - chat table
                with Container(id="top-container"):
                    yield DataTable(id="chat-table")
                
                # Bottom container - Selected chat display
                with Container(id="bottom-container"):
                    with Horizontal():
                        # Left side - Tree view for chat structure
                        with Container(id="tree-container"):
                            yield Tree("Chat", id="chat-tree")
                        
                        # Right side - Message details
                        with Container(id="details-container"):
                            with Vertical():
                                # Message detail pane with scrollable container
                                with Container(id="detail-container"):
                                    with ScrollableContainer(id="message-scroll"):
                                        message_detail = Static("Select a message to view details", id="message-detail")
                                        message_detail.can_focus = True
                                        yield message_detail
                                
                                # Raw content pane with scrollable container
                                with Container(id="raw-container"):
                                    with ScrollableContainer(id="raw-scroll"):
                                        raw_content = Static("", id="raw-content")
                                        raw_content.can_focus = True
                                        yield raw_content
                
        yield Footer()
    
    def on_mount(self) -> None:
        """Set up border titles and populate DataTable after mounting"""
        # Set initial border titles
        top_container = self.query_one("#top-container", Container)
        top_container.border_title = "Select Chat"
        
        bottom_container = self.query_one("#bottom-container", Container)
        bottom_container.border_title = f"Chat: {self.selected_chat}"
        
        # Set tree and detail pane titles
        tree_container = self.query_one("#tree-container", Container)
        tree_container.border_title = "Chat Structure"
        
        tree = self.query_one("#chat-tree", Tree)
        tree.border_title = ""  # Remove tree's own border title since container has it
        
        detail_container = self.query_one("#detail-container", Container)
        detail_container.border_title = "Message Details"
        
        raw_container = self.query_one("#raw-container", Container)
        raw_container.border_title = "Raw Content"
        
        # Set up DataTable
        self._setup_chat_table()
    
    def _setup_chat_table(self) -> None:
        """Set up the chat DataTable with columns and data"""
        table = self.query_one("#chat-table", DataTable)
        
        # Add columns with sorting enabled
        table.add_column("Chat ID", width=10, key="chat_id")
        table.add_column("Prompt Name", width=18, key="prompt_name")
        table.add_column("Filename", width=25, key="prompt_filename")
        table.add_column("Version", width=8, key="version")
        table.add_column("Created", width=16, key="created_timestamp")
        table.add_column("Cost", width=10, key="cost")
        
        # Populate with chat data
        for conv in self.chats:
            # Format the created timestamp
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(conv['created_timestamp'].replace('Z', '+00:00'))
                created_str = dt.strftime("%m/%d/%y %H:%M:%S")
            except:
                created_str = "Unknown"
            
            # Format the cost
            cost_str = f"${conv['total_cost']:.4f}"
            
            # Handle empty prompt_filename
            filename = conv.get('prompt_filename', '') or '[No file]'
            
            # Add row with chat_id as the key for selection
            table.add_row(
                conv['chat_id'],
                conv['prompt_name'] or '[No name]',
                filename,
                conv['prompt_version'] or '[No version]',
                created_str,
                cost_str,
                key=conv['chat_id']
            )
        
        # Enable cursor and sorting
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.sort("created_timestamp", reverse=True)  # Sort by newest first
        
        # Select initial chat if specified
        if self.initial_chat_name and self.initial_chat_name in [c['chat_id'] for c in self.chats]:
            # Find the row and move cursor to it
            try:
                row_index = table.get_row_index(self.initial_chat_name)
                table.move_cursor(row=row_index)
                # Trigger the selection event to populate other containers
                self.call_after_refresh(self._auto_select_chat, self.initial_chat_name)
            except:
                # If move_cursor doesn't work, we'll just let the user select manually
                pass
    
    def _auto_select_chat(self, chat_id: str) -> None:
        """Automatically select and populate chat data for the specified chat ID"""
        self.selected_chat = chat_id
        
        # Update the bottom container's title
        bottom_container = self.query_one("#bottom-container", Container)
        bottom_container.border_title = f"Chat: {self.selected_chat}"
        
        # Load and display chat data
        self._populate_chat_tree(chat_id)
    
    def _populate_chat_tree(self, chat_name: str) -> None:
        """Populate the tree with chat data"""
        self.chat_data = self._load_chat(chat_name)
        if not self.chat_data:
            return
        
        tree = self.query_one("#chat-tree", Tree)
        tree.clear()
        
        # Root node
        root = tree.root
        root.set_label(f"📁 {chat_name}")
        
        # VM State section
        vm_state = self.chat_data.get('vm_state', {})
        if vm_state:
            vm_node = root.add(f"📋 VM State ({vm_state.get('interaction_no', 0)} interactions)")
            vm_node.data = {'type': 'vm_state', 'content': vm_state}
            
            # Add VM state details as children
            for key, value in vm_state.items():
                vm_node.add(f"{key}: {value}")
        
        # Messages section
        messages = self.chat_data.get('messages', [])
        if messages:
            messages_node = root.add(f"💬 Messages ({len(messages)} total)")
            messages_node.data = {'type': 'messages_header', 'content': messages}
            
            # Add individual messages
            for i, message in enumerate(messages):
                role = message.get('role', 'unknown')
                content = message.get('content', [])
                
                # Extract text content from various message types
                text_content = ""
                if isinstance(content, list) and content:
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict):
                            item_type = item.get('type', '')
                            
                            # Handle text content
                            if item_type == 'text':
                                text_parts.append(item.get('text', ''))
                            
                            # Handle tool calls (function calls from assistant)
                            elif item_type in ('tool', 'call'):
                                name = item.get('name', 'unknown')
                                args = item.get('arguments', {})
                                call_id = item.get('id', '')
                                # Format as function call
                                args_str = ', '.join(f"{k}={v}" for k, v in args.items()) if isinstance(args, dict) else str(args)
                                text_parts.append(f"Call {name}({args_str}) [id={call_id}]")
                            
                            # Handle tool results (function returns)
                            elif item_type in ('tool_result', 'result'):
                                name = item.get('name', 'unknown')
                                result = item.get('content', item.get('result', ''))
                                call_id = item.get('tool_use_id', item.get('id', ''))
                                # Format as function result
                                result_preview = str(result)[:100] + '...' if len(str(result)) > 100 else str(result)
                                text_parts.append(f"Result {name}(): {result_preview} [id={call_id}]")
                    
                    text_content = '\n'.join(text_parts) if text_parts else ""
                elif isinstance(content, str):
                    text_content = content
                
                # Create message preview
                icon = self._get_role_icon(role)
                preview = self._truncate_text(text_content) if text_content else "[Empty message]"
                
                msg_node = messages_node.add(f"{icon} {role.title()}: {preview}")
                msg_node.data = {
                    'type': 'message',
                    'index': i,
                    'role': role,
                    'content': text_content,
                    'full_message': message
                }
        
        # Variables section
        variables = self.chat_data.get('variables', {})
        if variables:
            vars_node = root.add(f"🔧 Variables ({len(variables)} items)")
            vars_node.data = {'type': 'variables', 'content': variables}
            
            # Add variable details as children
            for key, value in variables.items():
                var_preview = self._truncate_text(str(value), 40)
                vars_node.add(f"{key}: {var_preview}")
        
        # Expand the root and messages by default
        root.expand()
        if messages:
            messages_node.expand()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle chat selection from DataTable"""
        if event.data_table.id == "chat-table":
            # Get the chat_id from the row key value
            self.selected_chat = str(event.row_key.value)
            
            # Update the bottom container's title
            bottom_container = self.query_one("#bottom-container", Container)
            bottom_container.border_title = f"Chat: {self.selected_chat}"
            
            # Load and display chat data
            self._populate_chat_tree(self.selected_chat)
    
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection to show message details"""
        node = event.node
        if not hasattr(node, 'data') or not node.data:
            return
        
        detail_widget = self.query_one("#message-detail", Static)
        raw_widget = self.query_one("#raw-content", Static)
        detail_container = self.query_one("#detail-container", Container)
        raw_container = self.query_one("#raw-container", Container)
        
        node_type = node.data.get('type')
        
        if node_type == 'message':
            # Show full message content
            role = node.data.get('role', 'unknown')
            content = node.data.get('content', '')
            full_message = node.data.get('full_message', {})
            
            icon = self._get_role_icon(role)
            
            # Store current message content and role for markdown toggle
            self.current_message_content = content
            self.current_message_role = role
            
            # Update border title with section name
            detail_container.border_title = f"{icon} {role.upper()} MESSAGE"
            
            # Use the new update method that respects markdown mode
            self._update_message_display(content, role)
            
            # Show raw content in separate container
            raw_container.border_title = "Raw Content"
            if 'content' in full_message and isinstance(full_message['content'], list):
                raw_widget.update(json.dumps(full_message['content'], indent=4, ensure_ascii=False))
            else:
                raw_widget.update(json.dumps(full_message, indent=4, ensure_ascii=False))
            
        elif node_type == 'vm_state':
            # Clear message content since this is not a message
            self.current_message_content = ""
            self.current_message_role = ""
            
            # Show VM state details
            vm_state = node.data.get('content', {})
            
            # Update border title with section name
            detail_container.border_title = "📋 VM STATE"
            
            # Show formatted VM state as table
            table_text = self._format_as_table(vm_state, "Variable")
            detail_widget.update(table_text)
            
            # Show raw JSON in separate container
            raw_container.border_title = "Raw VM State"
            raw_widget.update(json.dumps(vm_state, indent=4, ensure_ascii=False))
            
        elif node_type == 'variables':
            # Clear message content since this is not a message
            self.current_message_content = ""
            self.current_message_role = ""
            
            # Show variables details
            variables = node.data.get('content', {})
            
            # Update border title with section name
            detail_container.border_title = "🔧 VARIABLES"
            
            # Show formatted variables as table
            table_text = self._format_as_table(variables, "Variable")
            detail_widget.update(table_text)
            
            # Show raw JSON in separate container
            raw_container.border_title = "Raw Variables"
            raw_widget.update(json.dumps(variables, indent=4, ensure_ascii=False))
            
        else:
            # Clear message content since this is not a message
            self.current_message_content = ""
            self.current_message_role = ""
            
            detail_container.border_title = "Message Details"
            raw_container.border_title = "Raw Content"
            detail_widget.update("Select a message to view details")
            raw_widget.update("")
    
    def action_copy_text(self) -> None:
        """Copy text from Static widgets to clipboard"""
        try:
            # Get the currently focused widget to determine which container to copy from
            focused = self.app.focused
            text_to_copy = ""
            feedback_container = None
            
            # Check if focus is on raw content or message detail
            detail_widget = self.query_one("#message-detail", Static)
            raw_widget = self.query_one("#raw-content", Static)
            detail_container = self.query_one("#detail-container", Container)
            raw_container = self.query_one("#raw-container", Container)
            
            # Determine which widget to copy from based on focus or content
            if focused == raw_widget or (hasattr(focused, 'parent') and focused.parent == raw_container):
                # Copy from raw content
                if hasattr(raw_widget, 'renderable') and raw_widget.renderable:
                    text_to_copy = str(raw_widget.renderable)
                elif hasattr(raw_widget, 'text'):
                    text_to_copy = raw_widget.text
                feedback_container = raw_container
            else:
                # Copy from message detail (default)
                if hasattr(detail_widget, 'renderable') and detail_widget.renderable:
                    rich_text = str(detail_widget.renderable)
                    text_to_copy = self._extract_plain_text(rich_text)
                elif hasattr(detail_widget, 'text'):
                    text_to_copy = self._extract_plain_text(detail_widget.text)
                feedback_container = detail_container
            
            # If no content in focused widget, try the other one
            if not text_to_copy or not text_to_copy.strip():
                if feedback_container == raw_container:
                    # Try message detail
                    if hasattr(detail_widget, 'renderable') and detail_widget.renderable:
                        rich_text = str(detail_widget.renderable)
                        text_to_copy = self._extract_plain_text(rich_text)
                    elif hasattr(detail_widget, 'text'):
                        text_to_copy = self._extract_plain_text(detail_widget.text)
                    feedback_container = detail_container
                else:
                    # Try raw content
                    if hasattr(raw_widget, 'renderable') and raw_widget.renderable:
                        text_to_copy = str(raw_widget.renderable)
                    elif hasattr(raw_widget, 'text'):
                        text_to_copy = raw_widget.text
                    feedback_container = raw_container
            
            if text_to_copy and text_to_copy.strip():
                # Simple copy - just set to clipboard if available
                try:
                    if hasattr(self.app, 'copy_to_clipboard'):
                        self.app.copy_to_clipboard(text_to_copy)
                    
                    # Show success feedback
                    original_title = feedback_container.border_title
                    feedback_container.border_title = "✅ COPIED TO CLIPBOARD!"
                    self.set_timer(2.0, lambda: setattr(feedback_container, 'border_title', original_title))
                    
                except Exception:
                    # Show feedback that copy was attempted
                    original_title = feedback_container.border_title
                    feedback_container.border_title = "📋 COPY ATTEMPTED"
                    self.set_timer(2.0, lambda: setattr(feedback_container, 'border_title', original_title))
            else:
                # No content to copy
                original_title = feedback_container.border_title
                feedback_container.border_title = "❌ NO CONTENT TO COPY"
                self.set_timer(2.0, lambda: setattr(feedback_container, 'border_title', original_title))
                
        except Exception as e:
            # Show error feedback on detail container as fallback
            detail_container = self.query_one("#detail-container", Container)
            original_title = detail_container.border_title
            detail_container.border_title = f"❌ COPY FAILED: {str(e)[:30]}"
            self.set_timer(3.0, lambda: setattr(detail_container, 'border_title', original_title))
    
    def action_select_all(self) -> None:
        """Select all - simplified for Static widgets"""
        # Since Static widgets don't support text selection, just show feedback
        try:
            detail_container = self.query_one("#detail-container", Container)
            original_title = detail_container.border_title
            detail_container.border_title = "📝 Press F5/C to copy content"
            self.set_timer(2.0, lambda: setattr(detail_container, 'border_title', original_title))
        except Exception:
            pass
    
    def action_quit(self) -> None:
        """Quit the application"""
        self.app.exit()
    
    def action_back(self) -> None:
        """Go back"""
        self.app.pop_screen()
    
    def action_toggle_markdown(self) -> None:
        """Toggle between text and markdown rendering modes"""
        self.markdown_mode = not self.markdown_mode
        
        # Update the current message display if we have content
        if self.current_message_content and self.current_message_role:
            self._update_message_display(self.current_message_content, self.current_message_role)
        
        # Show feedback about the toggle
        detail_container = self.query_one("#detail-container", Container)
        mode_text = "🎨 MARKDOWN MODE" if self.markdown_mode else "📝 TEXT MODE"
        original_title = detail_container.border_title
        
        # Extract the base title (remove existing mode indicator)
        base_title = original_title
        if " - " in original_title:
            base_title = original_title.split(" - ")[0]
        
        # Update title with mode indicator
        detail_container.border_title = f"{base_title} - {mode_text}"
        
        # Reset to original title after 2 seconds
        self.set_timer(2.0, lambda: setattr(detail_container, 'border_title', base_title))
    
    def action_sort_menu(self) -> None:
        """Show sort menu for table columns"""
        table = self.query_one("#chat-table", DataTable)
        
        # Get current sort column and direction
        current_sort = getattr(table, '_sort_key', 'created_timestamp')
        current_reverse = getattr(table, '_sort_reverse', True)
        
        # Create sort options
        sort_options = [
            ("Created (Newest First)", "created_timestamp", True),
            ("Created (Oldest First)", "created_timestamp", False),
            ("Chat ID (A-Z)", "chat_id", False),
            ("Chat ID (Z-A)", "chat_id", True),
            ("Prompt Name (A-Z)", "prompt_name", False),
            ("Prompt Name (Z-A)", "prompt_name", True),
            ("Filename (A-Z)", "prompt_filename", False),
            ("Filename (Z-A)", "prompt_filename", True),
            ("Cost (Low to High)", "cost", False),
            ("Cost (High to Low)", "cost", True),
        ]
        
        # Find current selection
        current_index = 0
        for i, (_, key, reverse) in enumerate(sort_options):
            if key == current_sort and reverse == current_reverse:
                current_index = i
                break
        
        # Show sort selection (simplified - just cycle through options for now)
        next_index = (current_index + 1) % len(sort_options)
        _, sort_key, sort_reverse = sort_options[next_index]
        
        # Apply sort
        table.sort(sort_key, reverse=sort_reverse)
        table._sort_key = sort_key
        table._sort_reverse = sort_reverse
        
        # Update title to show current sort
        top_container = self.query_one("#top-container", Container)
        sort_name = sort_options[next_index][0]
        top_container.border_title = f"Chats - Sorted by {sort_name}"
    
    def _refresh_chat_list(self) -> None:
        """Refresh the chat table display"""
        table = self.query_one("#chat-table", DataTable)
        table.clear()
        
        # Re-add columns with new structure
        table.add_column("Chat ID", width=10, key="chat_id")
        table.add_column("Prompt Name", width=18, key="prompt_name")
        table.add_column("Filename", width=25, key="prompt_filename")
        table.add_column("Version", width=8, key="version")
        table.add_column("Created", width=16, key="created_timestamp")
        table.add_column("Cost", width=10, key="cost")
        
        # Re-populate with filtered chat data
        for conv in self.chats:
            # Format the created timestamp
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(conv['created_timestamp'].replace('Z', '+00:00'))
                created_str = dt.strftime("%m/%d/%y %H:%M:%S")
            except:
                created_str = "Unknown"
            
            # Format the cost
            cost_str = f"${conv['total_cost']:.4f}"
            
            # Handle empty prompt_filename
            filename = conv.get('prompt_filename', '') or '[No file]'
            
            # Add row with chat_id as the key for selection
            table.add_row(
                conv['chat_id'],
                conv['prompt_name'] or '[No name]',
                filename,
                conv['prompt_version'] or '[No version]',
                created_str,
                cost_str,
                key=conv['chat_id']
            )
        
        # Enable cursor and sorting
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.sort("created_timestamp", reverse=True)  # Sort by newest first


class chatViewerApp(App):
    """Main Textual application for viewing chats"""
    
    def on_unmount(self) -> None:
        """Clean up resources when app is unmounted"""
        pass
    
    async def action_quit(self) -> None:
        """Quit the application with proper cleanup"""
        self.exit()
    
    def exit(self, return_code: int = 0, message: str | None = None) -> None:
        """Override exit to ensure proper cleanup"""
        # Call parent exit method
        super().exit(return_code, message)
    
    CSS = """
    #main-container {
        padding: 0;
        margin: 0;
    }
    
    #top-container {
        height: 12;
        border: solid $primary;
        padding: 0;
        margin: 0;
    }
    
    #bottom-container {
        height: 1fr;
        border: solid $accent;
        padding: 0;
        margin: 0;
    }
    
    #tree-container {
        width: 1fr;
        border: solid $secondary;
        padding: 0;
        margin: 0;
    }
    
    #details-container {
        width: 2fr;
        padding: 0;
        margin: 0;
    }
    
    #chat-table {
        height: 1fr;
        padding: 0;
        margin: 0;
    }
    
    #chat-tree {
        height: 1fr;
        margin: 0;
        padding: 0;
    }
    
    #detail-container {
        height: 1fr;
        border: solid $warning;
        margin: 0;
        padding: 0;
    }
    
    #raw-container {
        height: 1fr;
        border: solid $success;
        margin: 0;
        padding: 0;
    }
    
    #message-scroll {
        height: 1fr;
        margin: 0;
        padding: 0;
    }
    
    #raw-scroll {
        height: 1fr;
        margin: 0;
        padding: 0;
    }
    
    #message-detail {
        padding: 1;
        margin: 0;
        background: $surface;
    }
    
    #message-detail:focus {
        border: solid $accent;
    }
    
    #raw-content {
        padding: 1;
        margin: 0;
        background: $surface;
    }
    
    #raw-content:focus {
        border: solid $accent;
    }
    """
    
    def __init__(self, chat_name: str):
        super().__init__()
        self.chat_name = chat_name
    
    def on_mount(self) -> None:
        """Initialize the app"""
        self.title = f"Chat Viewer - {self.chat_name}"
        self.push_screen(ChatViewer(self.chat_name))


def view_chat_tui(chat_id: str):
    """Launch the TUI chat viewer"""
    app = chatViewerApp(chat_id)
    app.run()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print("Usage: python chat_viewer.py")
        sys.exit(1)
    
    view_chat_tui("")
