"""
Textual-based conversation viewer for keprompt debug conversations.
Provides a collapsible, interactive view of conversation messages and function calls.
"""

import json
import asyncio
import warnings
from pathlib import Path
from typing import List

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Label, ListView, ListItem, Tree, Static, Input, Button
from textual.binding import Binding
from textual.screen import Screen, ModalScreen

# Suppress ResourceWarning for unclosed client sessions
warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*client_session")


class FilterPopup(ModalScreen[str]):
    """Modal screen for changing the filter"""
    
    def __init__(self, current_filter: str = ""):
        super().__init__()
        self.current_filter = current_filter
    
    def compose(self) -> ComposeResult:
        with Container(id="filter-popup"):
            yield Label("Enter filter for conversations:")
            yield Input(value=self.current_filter, placeholder="Enter filter text (empty for all)", id="filter-input")
            with Horizontal():
                yield Button("OK", variant="primary", id="ok-button")
                yield Button("Cancel", variant="default", id="cancel-button")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok-button":
            filter_input = self.query_one("#filter-input", Input)
            self.dismiss(filter_input.value)
        elif event.button.id == "cancel-button":
            self.dismiss(None)
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input field"""
        self.dismiss(event.value)


class ConversationViewer(Screen):
    """Main conversation viewing screen"""
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "back", "Back"),
        Binding("f5", "copy_text", "Copy Text"),
        Binding("f6", "select_all", "Select All"),
        Binding("c", "copy_text", "Copy"),
        Binding("a", "select_all", "Select All"),
        Binding("t", "toggle_left_panel", "Toggle Panel"),
    ]
    
    def __init__(self, initial_conversation_name: str = "", filter_arg: str = ""):
        super().__init__()
        self.initial_conversation_name = initial_conversation_name
        self.filter_arg = filter_arg
        self.selected_conversation = initial_conversation_name or "No conversation selected"
        self.conversations = self._get_all_conversations()
        self.conversation_data = None
        self.left_container_collapsed = False
        
    def _get_all_conversations(self) -> List[str]:
        """Get list of all available conversations, filtered by filter_arg"""
        conversations_dir = Path('conversations')
        if not conversations_dir.exists():
            return []
        
        conversation_files = list(conversations_dir.glob('*.conversation'))
        all_conversations = sorted([f.stem for f in conversation_files])
        
        # Apply filter if one is set
        if self.filter_arg:
            filtered_conversations = []
            filter_lower = self.filter_arg.lower()
            for conv in all_conversations:
                if filter_lower in conv.lower():
                    filtered_conversations.append(conv)
            return filtered_conversations
        
        return all_conversations
    
    def _load_conversation(self, conversation_name: str) -> dict:
        """Load conversation data from file"""
        conversation_file = Path('conversations') / f"{conversation_name}.conversation"
        if not conversation_file.exists():
            return {}
        
        try:
            with open(conversation_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
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
        
    def compose(self) -> ComposeResult:
        """Create the UI layout"""
        yield Header()
        
        with Container(id="main-container"):
            with Horizontal():
                # Left container - Conversation list
                with Container(id="left-container"):
                    # Create list items for conversations
                    list_items = []
                    for conv in self.conversations:
                        list_items.append(ListItem(Label(conv)))
                    
                    yield ListView(*list_items, id="conversation-list")
                
                # Right container - Selected conversation display
                with Container(id="right-container"):
                    with Vertical():
                        # Tree view for conversation structure
                        yield Tree("Conversation", id="conversation-tree")
                        
                        # Message detail pane
                        with Container(id="detail-container"):
                            message_detail = Static("Select a message to view details", id="message-detail")
                            message_detail.can_focus = True
                            yield message_detail
                        
                        # Raw content pane
                        with Container(id="raw-container"):
                            raw_content = Static("", id="raw-content")
                            raw_content.can_focus = True
                            yield raw_content
                
        yield Footer()
    
    def on_mount(self) -> None:
        """Set up border titles after mounting"""
        # Set initial border titles
        left_container = self.query_one("#left-container", Container)
        if self.filter_arg:
            left_container.border_title = f"Select Conversations with {self.filter_arg}"
        else:
            left_container.border_title = "Select Conversation"
        
        right_container = self.query_one("#right-container", Container)
        right_container.border_title = f"Conversation: {self.selected_conversation}"
        
        # Set tree and detail pane titles
        tree = self.query_one("#conversation-tree", Tree)
        tree.border_title = "Conversation Structure"
        
        detail_container = self.query_one("#detail-container", Container)
        detail_container.border_title = "Message Details"
        
        raw_container = self.query_one("#raw-container", Container)
        raw_container.border_title = "Raw Content"
    
    def _populate_conversation_tree(self, conversation_name: str) -> None:
        """Populate the tree with conversation data"""
        self.conversation_data = self._load_conversation(conversation_name)
        if not self.conversation_data:
            return
        
        tree = self.query_one("#conversation-tree", Tree)
        tree.clear()
        
        # Root node
        root = tree.root
        root.set_label(f"📁 {conversation_name}")
        
        # VM State section
        vm_state = self.conversation_data.get('vm_state', {})
        if vm_state:
            vm_node = root.add(f"📋 VM State ({vm_state.get('interaction_no', 0)} interactions)")
            vm_node.data = {'type': 'vm_state', 'content': vm_state}
            
            # Add VM state details as children
            for key, value in vm_state.items():
                vm_node.add(f"{key}: {value}")
        
        # Messages section
        messages = self.conversation_data.get('messages', [])
        if messages:
            messages_node = root.add(f"💬 Messages ({len(messages)} total)")
            messages_node.data = {'type': 'messages_header', 'content': messages}
            
            # Add individual messages
            for i, message in enumerate(messages):
                role = message.get('role', 'unknown')
                content = message.get('content', [])
                
                # Extract text content
                text_content = ""
                if isinstance(content, list) and content:
                    for item in content:
                        if isinstance(item, dict) and item.get('type') == 'text':
                            text_content = item.get('text', '')
                            break
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
        variables = self.conversation_data.get('variables', {})
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

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle conversation selection"""
        if event.list_view.id == "conversation-list":
            # Get the selected conversation name
            selected_item = event.item
            if selected_item and hasattr(selected_item, 'children'):
                label_widget = selected_item.children[0]  # Get the Label widget
                if hasattr(label_widget, 'renderable'):
                    self.selected_conversation = str(label_widget.renderable)
                    
                    # Update the right container's title
                    right_container = self.query_one("#right-container", Container)
                    right_container.border_title = f"Conversation: {self.selected_conversation}"
                    
                    # Load and display conversation data
                    self._populate_conversation_tree(self.selected_conversation)
    
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
            
            # Update border title with section name
            detail_container.border_title = f"{icon} {role.upper()} MESSAGE"
            
            # Show text content with special formatting for assistant messages
            if content:
                if role == 'assistant':
                    # Apply special parsing for assistant messages
                    formatted_content = self._parse_assistant_message(content)
                    detail_widget.update(formatted_content)
                else:
                    # Regular display for other roles
                    detail_widget.update(content)
            else:
                detail_widget.update("[Empty message]")
            
            # Show raw content in separate container
            raw_container.border_title = "Raw Content"
            if 'content' in full_message and isinstance(full_message['content'], list):
                raw_widget.update(json.dumps(full_message['content'], indent=4, ensure_ascii=False))
            else:
                raw_widget.update(json.dumps(full_message, indent=4, ensure_ascii=False))
            
        elif node_type == 'vm_state':
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
    
    def action_toggle_left_panel(self) -> None:
        """Toggle the left panel between collapsed and expanded state"""
        left_container = self.query_one("#left-container", Container)
        
        if self.left_container_collapsed:
            # Expand the panel
            left_container.styles.width = "1fr"
            if self.filter_arg:
                left_container.border_title = f"Select Conversations with {self.filter_arg}"
            else:
                left_container.border_title = "Select Conversation"
            self.left_container_collapsed = False
        else:
            # Collapse the panel
            left_container.styles.width = "5"
            left_container.border_title = "≡"
            self.left_container_collapsed = True
    
    def on_click(self, event) -> None:
        """Handle click events"""
        # Check if click is on the left container border title area
        left_container = self.query_one("#left-container", Container)
        if event.widget == left_container and not self.left_container_collapsed:
            # Show filter popup
            self.app.push_screen(FilterPopup(self.filter_arg), self._handle_filter_change)
    
    def _handle_filter_change(self, new_filter: str | None) -> None:
        """Handle filter change from popup"""
        if new_filter is not None:  # None means cancelled
            self.filter_arg = new_filter
            left_container = self.query_one("#left-container", Container)
            if self.filter_arg:
                left_container.border_title = f"Select Conversations with {self.filter_arg}"
            else:
                left_container.border_title = "Select Conversation"
            
            # Refresh conversation list with new filter
            self.conversations = self._get_all_conversations()
            self._refresh_conversation_list()
    
    def _refresh_conversation_list(self) -> None:
        """Refresh the conversation list display"""
        conversation_list = self.query_one("#conversation-list", ListView)
        conversation_list.clear()
        
        # Add filtered conversations to the list
        for conv in self.conversations:
            conversation_list.append(ListItem(Label(conv)))


class ConversationViewerApp(App):
    """Main Textual application for viewing conversations"""
    
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
    
    #left-container {
        width: 1fr;
        border: solid $primary;
        padding: 0;
        margin: 0;
    }
    
    #right-container {
        width: 2fr;
        border: solid $accent;
        padding: 0;
        margin: 0;
    }
    
    #conversation-list {
        height: 1fr;
        padding: 0;
        margin: 0;
    }
    
    #conversation-tree {
        height: 2fr;
        border: solid $secondary;
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
    
    #message-detail {
        padding: 0;
        margin: 0;
        height: 1fr;
        overflow-y: auto;
        background: $surface;
    }
    
    #message-detail:focus {
        border: solid $accent;
    }
    
    #raw-content {
        padding: 0;
        margin: 0;
        height: 1fr;
        overflow-y: auto;
        background: $surface;
    }
    
    #raw-content:focus {
        border: solid $accent;
    }
    
    #filter-popup {
        width: 60;
        height: 10;
        background: $surface;
        border: solid $primary;
        padding: 1;
        margin: 1;
    }
    
    #filter-input {
        width: 1fr;
        margin: 1 0;
    }
    """
    
    def __init__(self, conversation_name: str, filter_arg: str = ""):
        super().__init__()
        self.conversation_name = conversation_name
        self.filter_arg = filter_arg
    
    def on_mount(self) -> None:
        """Initialize the app"""
        self.title = f"Conversation Viewer - {self.conversation_name}"
        self.push_screen(ConversationViewer(self.conversation_name, self.filter_arg))


def view_conversation_tui(conversation_name: str, filter_arg: str = ""):
    """Launch the TUI conversation viewer"""
    app = ConversationViewerApp(conversation_name, filter_arg)
    app.run()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        print("Usage: python conversation_viewer.py [filter_arg]")
        sys.exit(1)
    
    filter_arg = sys.argv[1] if len(sys.argv) == 2 else ""
    view_conversation_tui("", filter_arg)
