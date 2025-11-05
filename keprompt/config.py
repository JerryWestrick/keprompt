"""
Configuration management for KePrompt.

Handles loading configuration from TOML files and environment variables.
"""

import os
import toml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class Config:
    """Configuration manager for KePrompt."""
    
    def __init__(self):
        self._config = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from files and environment variables."""
        # Default configuration
        self._config = {
            'database': {
                'url': 'sqlite:///prompts/chats.db'
            },
            'chats': {
                'enabled': True,  # Enabled by default - all executions create chats
                'auto_cleanup': False,
                'max_days': 30,
                'max_size_gb': 2.0,
                'max_count': 5000
            },
            'env': {
                'file_path': str(Path.home() / '.env')  # Default to ~/.env
            }
        }
        
        # Load from config file if it exists
        config_paths = [
            Path.home() / '.keprompt' / 'config.toml',
            Path.cwd() / 'keprompt.toml',
            Path.cwd() / '.keprompt.toml'
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                try:
                    file_config = toml.load(config_path)
                    self._merge_config(file_config)
                    break
                except Exception as e:
                    print(f"Warning: Error loading config from {config_path}: {e}")
        
        # Load .env file if configured
        self._load_env_file()
        
        # Override with environment variables
        self._load_env_overrides()
    
    def _merge_config(self, new_config: Dict[str, Any]):
        """Merge new configuration into existing config."""
        for section, values in new_config.items():
            if section not in self._config:
                self._config[section] = {}
            if isinstance(values, dict):
                self._config[section].update(values)
            else:
                self._config[section] = values
    
    def _load_env_overrides(self):
        """Load configuration overrides from environment variables."""
        # Database URL override
        db_url = os.getenv('KEPROMPT_DATABASE_URL') or os.getenv('DATABASE_URL')
        if db_url:
            self._config['database']['url'] = db_url
        
        # chats enabled override
        chats_enabled = os.getenv('KEPROMPT_CHATS')
        if chats_enabled is not None:
            self._config['chats']['enabled'] = chats_enabled.lower() in ('true', '1', 'yes', 'on')
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(section, {}).get(key, default)
    
    def get_database_url(self) -> str:
        """Get database URL."""
        return self.get('database', 'url', 'sqlite:///prompts/chats.db')
    
    def is_chats_enabled(self) -> bool:
        """Check if chats are enabled."""
        return self.get('chats', 'enabled', True)
    
    def get_cleanup_settings(self) -> Dict[str, Any]:
        """Get cleanup settings."""
        return {
            'max_days': self.get('chats', 'max_days', 30),
            'max_size_gb': self.get('chats', 'max_size_gb', 2.0),
            'max_count': self.get('chats', 'max_count', 5000)
        }
    
    def _load_env_file(self):
        """Load environment variables from .env file."""
        env_file_path = self.get('env', 'file_path', str(Path.home() / '.env'))
        env_path = Path(env_file_path)
        
        if env_path.exists():
            try:
                load_dotenv(env_path)
            except Exception as e:
                print(f"Warning: Error loading .env file from {env_path}: {e}")
    
    def get_env_file_path(self) -> str:
        """Get the path to the .env file."""
        return self.get('env', 'file_path', str(Path.home() / '.env'))
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a provider from environment variables."""
        # Try provider-specific environment variable first
        key_var = f"{provider.upper()}_API_KEY"
        api_key = os.getenv(key_var)
        
        if not api_key:
            # Try alternative naming conventions
            alt_key_var = f"{provider.upper()}_KEY"
            api_key = os.getenv(alt_key_var)
        
        return api_key
    
    def set_api_key(self, provider: str, api_key: str):
        """Set API key for a provider in the .env file. This is mainly for the --key command."""
        env_file_path = Path(self.get_env_file_path())
        key_var = f"{provider.upper()}_API_KEY"
        
        # Create .env file directory if it doesn't exist
        env_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read existing .env file content
        env_content = {}
        if env_file_path.exists():
            try:
                with open(env_file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env_content[key.strip()] = value.strip()
            except Exception as e:
                print(f"Warning: Error reading existing .env file: {e}")
        
        # Update the API key
        env_content[key_var] = api_key
        
        # Write back to .env file
        try:
            with open(env_file_path, 'w') as f:
                for key, value in env_content.items():
                    f.write(f"{key}={value}\n")
        except Exception as e:
            print(f"Error: Could not write to .env file {env_file_path}: {e}")
            raise
    
    def get_missing_key_error(self, provider: str) -> str:
        """Generate a helpful error message for missing API keys."""
        key_var = f"{provider.upper()}_API_KEY"
        env_file_path = self.get_env_file_path()
        
        return (
            f"API key not found: {key_var} is missing from {env_file_path}\n"
            f"Please add your {provider} API key to your .env file:\n"
            f"  echo '{key_var}=your_api_key_here' >> {env_file_path}\n"
            f"Or use: keprompt --key to interactively set API keys"
        )


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
