"""
HTTP REST API server for keprompt.
Provides web-based access to keprompt functionality via REST endpoints.
"""

import sys
import json
import argparse
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("ERROR: FastAPI dependencies not installed. Run: pip install fastapi uvicorn", file=sys.stderr)
    sys.exit(1)

from .api import handle_json_command
from .version import __version__


def build_args(command: str, subcommand: str, **kwargs) -> argparse.Namespace:
    """
    Build an argparse.Namespace for direct API calls.
    
    Args:
        command: The main command (e.g., 'chat', 'model', 'provider')
        subcommand: The subcommand (e.g., 'get', 'create', 'update', 'delete')
        **kwargs: Additional attributes to set on the namespace
    
    Returns:
        Configured argparse.Namespace ready for API calls
    """
    # Set the command-specific subcommand attribute
    subcommand_attr = f"{command}_command"
    
    args = argparse.Namespace(
        command=command,
        pretty=False,  # Always return data structures, not Rich tables
        format='json',  # Ensure JSON mode
        **kwargs
    )
    
    # Set the subcommand attribute dynamically
    setattr(args, subcommand_attr, subcommand)
    
    return args


class ChatCreate(BaseModel):
    """Request model for creating a new chat"""
    prompt: str
    params: Dict[str, str] = {}


class ChatUpdate(BaseModel):
    """Request model for updating a chat"""
    answer: str


class ErrorResponse(BaseModel):
    """Standard error response model (unchanged)"""
    status: str = "error"
    error: Dict[str, Any]


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title="KePrompt REST API",
        description="HTTP REST API for KePrompt - Prompt Engineering Tool",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Enable CORS for browser access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify actual origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app


def call_api(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Call the API directly with an argparse.Namespace.
    
    Args:
        args: Configured argparse.Namespace with command and parameters
        
    Returns:
        JSON response from the API
        
    Raises:
        HTTPException: If command fails
    """
    try:
        response = handle_json_command(args)
        
        # Ensure response is a dict
        if not isinstance(response, dict):
            # If it's not a dict, wrap it
            response = {"success": True, "data": response}
        
        # Check for errors in the response
        if not response.get("success", True):
            raise HTTPException(
                status_code=400,
                detail=response
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
        )


def setup_routes(app: FastAPI, enable_web_gui: bool = False) -> None:
    """Set up all REST API routes and optionally static file serving"""
    
    # First, define all API routes (these must come before static file mounting)
    
    # If web GUI is not enabled, provide API info at root
    if not enable_web_gui:
        @app.get("/")
        async def root():
            """Root endpoint with API information"""
            return {
                "status": "success",
                "data": {
                    "name": "KePrompt REST API",
                    "version": __version__,
                    "description": "HTTP REST API for KePrompt - Prompt Engineering Tool",
                    "endpoints": {
                        "prompts": "/api/prompts",
                        "models": "/api/models",
                        "providers": "/api/providers",
                        "companies": "/api/companies",
                        "functions": "/api/functions",
                        "chats": "/api/chats",
                        "database": "/api/database",
                        "builtins": "/api/builtins"
                    },
                    "documentation": {
                        "swagger": "/docs",
                        "redoc": "/redoc"
                    }
                }
            }
    
    # Resource Discovery Endpoints
    @app.get("/api/prompts")
    async def get_prompts(pattern: Optional[str] = None):
        """Get available prompts with optional pattern filtering"""
        args = build_args('prompt', 'get', name=pattern)
        return call_api(args)
    
    @app.get("/api/models")
    async def get_models(
        name: Optional[str] = None,
        provider: Optional[str] = None,
        company: Optional[str] = None
    ):
        """Get available models with optional filtering"""
        args = build_args('models', 'get', name=name, provider=provider, company=company)
        return call_api(args)
    
    @app.get("/api/providers")
    async def get_providers():
        """Get available API providers"""
        args = build_args('provider', 'list')
        return call_api(args)
    
    @app.get("/api/companies")
    async def get_companies():
        """Get available model companies"""
        # Companies are accessed through models API
        from .api import ResourceDiscovery
        return ResourceDiscovery.get_companies()
    
    @app.get("/api/functions")
    async def get_functions():
        """Get available functions"""
        args = build_args('functions', 'get')
        return call_api(args)
    
    # Chat Management Endpoints
    @app.get("/api/chats")
    async def get_chats(limit: Optional[int] = None):
        """Get all available chats"""
        args = build_args('chat', 'get', chat_id=None, limit=limit)
        return call_api(args)
    
    @app.get("/api/chats/{chat_id}")
    async def get_chat(chat_id: str):
        """Get detailed chat information"""
        args = build_args('chat', 'get', chat_id=chat_id, limit=None)
        return call_api(args)
    
    @app.post("/api/chats")
    async def create_chat(chat_data: ChatCreate):
        """Create a new chat"""
        # Convert params dict to list format expected by ChatManager
        param_list = []
        for key, value in chat_data.params.items():
            param_list.append([key, value])
        
        args = build_args('chat', 'create', prompt=chat_data.prompt, param=param_list if param_list else None)
        return call_api(args)
    
    @app.put("/api/chats/{chat_id}/messages")
    async def update_chat(chat_id: str, update_data: ChatUpdate):
        """Add a message to an existing chat"""
        args = build_args('chat', 'update', chat_id=chat_id, answer=update_data.answer, message=None, full=False)
        return call_api(args)
    
    @app.delete("/api/chats/{chat_id}")
    async def delete_chat(chat_id: str):
        """Delete a chat"""
        args = build_args('chat', 'delete', chat_id=chat_id, max_days=None, max_count=None, max_size_gb=None)
        return call_api(args)
    
    # System Management Endpoints
    @app.get("/api/database")
    async def get_database():
        """Get database statistics"""
        args = build_args('database', 'get')
        return call_api(args)
    
    @app.post("/api/database")
    async def create_database():
        """Initialize database"""
        args = build_args('database', 'create')
        return call_api(args)
    
    @app.delete("/api/database")
    async def delete_database():
        """Delete database (nuclear option)"""
        # Database delete uses different subcommand
        args = build_args('database', 'delete', days=None, count=None, gb=None)
        return call_api(args)
    
    @app.put("/api/database")
    async def update_database(
        max_days: Optional[int] = None,
        max_count: Optional[int] = None,
        max_gb: Optional[float] = None
    ):
        """Clean up database with optional limits"""
        # For database cleanup/truncate
        args = build_args('database', 'delete', days=max_days, count=max_count, gb=max_gb)
        return call_api(args)
    
    @app.post("/api/workspace")
    async def create_workspace():
        """Initialize workspace directories"""
        from .api import SystemManagement
        return SystemManagement.create_workspace()
    
    @app.put("/api/models")
    async def update_models(provider: Optional[str] = None):
        """Update model definitions"""
        args = build_args('models', 'update', provider=provider)
        return call_api(args)
    
    @app.get("/api/builtins")
    async def get_builtins():
        """Get built-in functions status"""
        from .api import SystemManagement
        return SystemManagement.get_builtins_status()
    
    @app.put("/api/builtins")
    async def update_builtins():
        """Update built-in functions"""
        from .api import SystemManagement
        return SystemManagement.update_builtins()
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "success",
            "data": {
                "service": "keprompt-api",
                "version": __version__,
                "healthy": True
            }
        }
    
    # Mount static files LAST (after all API routes are defined)
    # This prevents static file serving from intercepting API routes
    if enable_web_gui:
        # Determine path to web_gui directory
        # This file is in keprompt/http_server.py, web_gui is in keprompt/web_gui
        current_file = Path(__file__)
        package_root = current_file.parent  # This is the keprompt/ directory
        web_gui_path = package_root / "web_gui"
        
        # Check if web_gui directory exists
        if web_gui_path.exists() and web_gui_path.is_dir():
            # Mount static files - this will serve the web GUI
            app.mount("/", StaticFiles(directory=str(web_gui_path), html=True), name="static")
            print(f"Web GUI enabled: serving from {web_gui_path}")
        else:
            print(f"Warning: web_gui directory not found at {web_gui_path}")
            print("Web GUI disabled - directory not available")


def parse_server_args(args: list[str]) -> argparse.Namespace:
    """Parse server-specific command line arguments"""
    parser = argparse.ArgumentParser(
        description="KePrompt HTTP REST API Server",
        prog="keprompt server"
    )
    
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind the server to (default: localhost)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to bind the server to (default: 8080)"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        default="info",
        help="Log level (default: info)"
    )
    
    parser.add_argument(
        "--web-gui",
        action="store_true",
        help="Enable web GUI interface (serves static files from web-gui/)"
    )
    
    return parser.parse_args(args)


def run_http_server(args: list[str] = None, working_directory: str = None) -> None:
    """
    Run the HTTP REST API server
    
    Args:
        args: Command line arguments (if None, uses sys.argv[2:])
        working_directory: Working directory for the server (defaults to cwd)
    """
    import signal
    import os
    from .server_registry import register_server, unregister_server, sync_registry, get_server
    
    if args is None:
        args = sys.argv[2:]  # Skip 'keprompt server'
    
    if working_directory is None:
        working_directory = os.getcwd()
    
    # Normalize to absolute path
    working_directory = str(Path(working_directory).resolve())
    
    # Auto-sync registry before starting
    sync_registry()
    
    # Check if server already running for this directory
    existing = get_server(working_directory)
    if existing and existing.status == 'running':
        print(f"ERROR: Server already running for {working_directory}")
        print(f"       Port: {existing.port}, PID: {existing.pid}")
        print(f"       Use 'keprompt server stop' to stop it first")
        sys.exit(1)
    
    try:
        # Parse arguments
        parsed_args = parse_server_args(args)
        
        # Create FastAPI app
        app = create_app()
        setup_routes(app, enable_web_gui=parsed_args.web_gui)
        
        # Update startup messages based on web GUI status
        if parsed_args.web_gui:
            print(f"Starting KePrompt REST API server with Web GUI...")
        else:
            print(f"Starting KePrompt REST API server (API only)...")
        
        print(f"Host: {parsed_args.host}")
        print(f"Port: {parsed_args.port}")
        print()
        
        if parsed_args.web_gui:
            print(f"🌐 Web Interface: http://{parsed_args.host}:{parsed_args.port}/")
        else:
            print(f"🔗 API Root: http://{parsed_args.host}:{parsed_args.port}/")
        
        print(f"📚 API Documentation: http://{parsed_args.host}:{parsed_args.port}/docs")
        print(f"❤️  Health Check: http://{parsed_args.host}:{parsed_args.port}/health")
        print()
        
        if not parsed_args.web_gui:
            print("💡 Tip: Add --web-gui flag to enable the web interface")
            print()
        
        print("Press Ctrl+C to stop the server")
        print()
        
        # Get the current process ID
        pid = os.getpid()
        
        # Register server in global registry
        register_server(
            directory=working_directory,
            port=parsed_args.port,
            pid=pid,
            web_gui_enabled=parsed_args.web_gui
        )
        
        # Setup signal handlers for graceful shutdown
        def shutdown_handler(signum, frame):
            print("\nShutting down server gracefully...")
            unregister_server(working_directory)
            sys.exit(0)
        
        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)
        
        try:
            # Run the server
            uvicorn.run(
                app,
                host=parsed_args.host,
                port=parsed_args.port,
                reload=parsed_args.reload,
                log_level=parsed_args.log_level
            )
        finally:
            # Ensure cleanup on any exit
            unregister_server(working_directory)
        
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        unregister_server(working_directory)
    except Exception as e:
        print(f"ERROR: Failed to start server: {e}", file=sys.stderr)
        unregister_server(working_directory)
        sys.exit(1)


if __name__ == "__main__":
    # Allow running the server directly
    run_http_server()
