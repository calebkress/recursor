#!/usr/bin/env python3
"""
Advanced Configuration Management System for Recursor
Supports environment-based configs, validation, and dynamic reloading
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

@dataclass
class APIConfig:
    """API configuration settings"""
    openai_model: str = "gpt-4-turbo"
    openai_api_key: Optional[str] = None
    openai_max_tokens: int = 4000
    openai_temperature: float = 0.1
    serpapi_api_key: Optional[str] = None
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_requests_per_minute: int = 60
    
    def __post_init__(self):
        # Load from environment if not provided
        if not self.openai_api_key:
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.serpapi_api_key:
            self.serpapi_api_key = os.getenv('SERPAPI_API_KEY')

@dataclass 
class ProcessingConfig:
    """Processing pipeline configuration"""
    batch_size: int = 10
    max_concurrent_requests: int = 5
    enable_caching: bool = True
    cache_ttl_hours: int = 24
    progress_update_interval: int = 1
    checkpoint_interval: int = 50
    enable_resume: bool = True
    temp_directory: str = "tmp"
    
@dataclass
class ScoringConfig:
    """Scoring system configuration"""
    default_template: str = "recurly_template.txt"
    templates_directory: str = "prompts/templates"
    enable_ab_testing: bool = False
    default_test_name: Optional[str] = None
    fallback_template: str = "recurly_template.txt"
    score_threshold_high: int = 75
    score_threshold_medium: int = 50
    
@dataclass
class ClusteringConfig:
    """Clustering analysis configuration"""
    default_method: str = "kmeans"
    auto_determine_clusters: bool = True
    max_clusters: int = 10
    min_cluster_size: int = 2
    random_seed: int = 42
    silhouette_threshold: float = 0.3
    enable_insights: bool = True
    
@dataclass
class EnrichmentConfig:
    """Data enrichment configuration"""
    max_search_results: int = 5
    enable_hiring_signals: bool = True
    enable_tech_stack: bool = True
    enable_news_mentions: bool = True
    search_result_cache_hours: int = 12
    
@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    file_path: str = "logs/recursor.log"
    console_enabled: bool = True
    max_file_size_mb: int = 10
    backup_count: int = 5

@dataclass
class RecursorConfig:
    """Master configuration class"""
    api: APIConfig = field(default_factory=APIConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig) 
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    clustering: ClusteringConfig = field(default_factory=ClusteringConfig)
    enrichment: EnrichmentConfig = field(default_factory=EnrichmentConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Meta settings
    environment: str = "development"
    debug: bool = False
    config_version: str = "1.0.0"
    
    @classmethod
    def load_from_file(cls, config_path: Union[str, Path]) -> 'RecursorConfig':
        """Load configuration from YAML or JSON file"""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            if config_path.suffix.lower() in ['.yml', '.yaml']:
                data = yaml.safe_load(f)
            elif config_path.suffix.lower() == '.json':
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {config_path.suffix}")
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecursorConfig':
        """Create configuration from dictionary"""
        config = cls()
        
        # Update nested configurations
        for section_name, section_data in data.items():
            if hasattr(config, section_name) and isinstance(section_data, dict):
                section_obj = getattr(config, section_name)
                for key, value in section_data.items():
                    if hasattr(section_obj, key):
                        setattr(section_obj, key, value)
            elif hasattr(config, section_name):
                setattr(config, section_name, section_data)
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        result = {}
        
        for field_name in self.__dataclass_fields__:
            field_value = getattr(self, field_name)
            if hasattr(field_value, '__dataclass_fields__'):
                # Nested dataclass
                result[field_name] = {
                    nested_field: getattr(field_value, nested_field)
                    for nested_field in field_value.__dataclass_fields__
                }
            else:
                result[field_name] = field_value
        
        return result
    
    def save_to_file(self, config_path: Union[str, Path]) -> None:
        """Save configuration to file"""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = self.to_dict()
        
        with open(config_path, 'w') as f:
            if config_path.suffix.lower() in ['.yml', '.yaml']:
                yaml.dump(data, f, default_flow_style=False, indent=2)
            elif config_path.suffix.lower() == '.json':
                json.dump(data, f, indent=2)
            else:
                raise ValueError(f"Unsupported config file format: {config_path.suffix}")
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        # API validation
        if not self.api.openai_api_key:
            issues.append("OpenAI API key not configured")
        if self.api.openai_max_tokens <= 0:
            issues.append("OpenAI max tokens must be positive")
        if not 0 <= self.api.openai_temperature <= 2:
            issues.append("OpenAI temperature must be between 0 and 2")
        
        # Processing validation
        if self.processing.batch_size <= 0:
            issues.append("Batch size must be positive")
        if self.processing.max_concurrent_requests <= 0:
            issues.append("Max concurrent requests must be positive")
        
        # Scoring validation
        templates_dir = Path(self.scoring.templates_directory)
        if not templates_dir.exists():
            issues.append(f"Templates directory not found: {templates_dir}")
        
        default_template_path = templates_dir / self.scoring.default_template
        if not default_template_path.exists():
            issues.append(f"Default template not found: {default_template_path}")
        
        # Clustering validation
        if self.clustering.max_clusters <= 1:
            issues.append("Max clusters must be greater than 1")
        if self.clustering.min_cluster_size <= 0:
            issues.append("Min cluster size must be positive")
        
        return issues
    
    def setup_logging(self):
        """Setup logging based on configuration"""
        logger = logging.getLogger('recursor')
        logger.setLevel(getattr(logging, self.logging.level.upper()))
        
        # Clear existing handlers
        logger.handlers.clear()
        
        formatter = logging.Formatter(self.logging.format)
        
        # Console handler
        if self.logging.console_enabled:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # File handler
        if self.logging.file_enabled:
            from logging.handlers import RotatingFileHandler
            
            log_path = Path(self.logging.file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=self.logging.max_file_size_mb * 1024 * 1024,
                backupCount=self.logging.backup_count
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger

class ConfigManager:
    """Configuration manager with environment support and hot reloading"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self._config: Optional[RecursorConfig] = None
        self._config_file_path: Optional[Path] = None
        self._last_modified: Optional[float] = None
        
    def load_config(self, environment: str = None) -> RecursorConfig:
        """Load configuration for specified environment"""
        if not environment:
            environment = os.getenv('RECURSOR_ENV', 'development')
        
        config_file = self.config_dir / f"{environment}.yml"
        
        # Try YAML first, then JSON
        if not config_file.exists():
            config_file = self.config_dir / f"{environment}.json"
        
        # Fall back to default config
        if not config_file.exists():
            config_file = self.config_dir / "default.yml"
            if not config_file.exists():
                config_file = self.config_dir / "default.json"
        
        # Create default config if none exists
        if not config_file.exists():
            self._config = RecursorConfig()
            self._config.environment = environment
            self.save_default_config()
            config_file = self.config_dir / "default.yml"
        
        self._config = RecursorConfig.load_from_file(config_file)
        self._config.environment = environment
        self._config_file_path = config_file
        self._last_modified = config_file.stat().st_mtime
        
        # Validate configuration
        issues = self._config.validate()
        if issues:
            logger = self._config.setup_logging()
            logger.warning(f"Configuration issues found: {issues}")
        
        return self._config
    
    def get_config(self, auto_reload: bool = True) -> RecursorConfig:
        """Get current configuration with optional auto-reload"""
        if not self._config:
            return self.load_config()
        
        # Check for file changes
        if auto_reload and self._config_file_path and self._config_file_path.exists():
            current_modified = self._config_file_path.stat().st_mtime
            if current_modified > self._last_modified:
                logger = self._config.setup_logging()
                logger.info("Configuration file changed, reloading...")
                return self.load_config(self._config.environment)
        
        return self._config
    
    def save_default_config(self) -> None:
        """Save default configuration template"""
        default_config = RecursorConfig()
        config_file = self.config_dir / "default.yml"
        default_config.save_to_file(config_file)
        
        # Also create environment-specific templates
        for env in ['development', 'production', 'testing']:
            env_config = RecursorConfig()
            env_config.environment = env
            
            # Adjust settings per environment
            if env == 'production':
                env_config.debug = False
                env_config.logging.level = "WARNING"
                env_config.processing.enable_caching = True
                env_config.api.request_timeout = 60
            elif env == 'development':
                env_config.debug = True
                env_config.logging.level = "DEBUG"
                env_config.processing.enable_caching = False
            elif env == 'testing':
                env_config.debug = True
                env_config.logging.level = "INFO"
                env_config.processing.batch_size = 2
                env_config.api.max_retries = 1
            
            env_file = self.config_dir / f"{env}.yml"
            if not env_file.exists():
                env_config.save_to_file(env_file)
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values"""
        if not self._config:
            self.load_config()
        
        # Apply updates
        for section_name, section_updates in updates.items():
            if hasattr(self._config, section_name):
                section_obj = getattr(self._config, section_name)
                if hasattr(section_obj, '__dataclass_fields__') and isinstance(section_updates, dict):
                    for key, value in section_updates.items():
                        if hasattr(section_obj, key):
                            setattr(section_obj, key, value)
                else:
                    setattr(self._config, section_name, section_updates)
        
        # Save updated config
        if self._config_file_path:
            self._config.save_to_file(self._config_file_path)
            self._last_modified = self._config_file_path.stat().st_mtime

# Global config manager instance
_config_manager = ConfigManager()

def get_config(environment: str = None, auto_reload: bool = True) -> RecursorConfig:
    """Get global configuration instance"""
    if environment:
        return _config_manager.load_config(environment)
    return _config_manager.get_config(auto_reload)

def update_config(updates: Dict[str, Any]) -> None:
    """Update global configuration"""
    _config_manager.update_config(updates)

def setup_logging() -> logging.Logger:
    """Setup logging from current configuration"""
    config = get_config()
    return config.setup_logging()

if __name__ == "__main__":
    # Demo usage
    config_manager = ConfigManager()
    config_manager.save_default_config()
    
    config = config_manager.load_config("development")
    print(f"Loaded config for {config.environment}")
    print(f"API model: {config.api.openai_model}")
    print(f"Batch size: {config.processing.batch_size}")
    print(f"Debug mode: {config.debug}")
    
    issues = config.validate()
    if issues:
        print(f"Configuration issues: {issues}")
    else:
        print("✅ Configuration is valid")
