#!/usr/bin/env python3
"""
Configuration Management CLI for Recursor
Manage environment configs, validation, and settings
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any
import yaml

# Import configuration management
from config.config_manager import ConfigManager, RecursorConfig, get_config, setup_logging

def init_config(args):
    """Initialize configuration files"""
    print("🚀 Initializing Recursor configuration...")
    
    config_manager = ConfigManager(args.config_dir)
    config_manager.save_default_config()
    
    print(f"✅ Configuration initialized in {args.config_dir}/")
    print("📁 Created configuration files:")
    
    config_dir = Path(args.config_dir)
    for config_file in config_dir.glob("*.yml"):
        print(f"   - {config_file.name}")
    
    print("\n🔧 Next steps:")
    print("   1. Update your API keys in the configuration files")
    print("   2. Customize settings for each environment")
    print("   3. Use 'python cli_config.py validate' to check your config")

def validate_config(args):
    """Validate configuration"""
    print(f"🔍 Validating configuration for environment: {args.environment}")
    
    try:
        config_manager = ConfigManager(args.config_dir)
        config = config_manager.load_config(args.environment)
        
        issues = config.validate()
        
        if not issues:
            print("✅ Configuration is valid!")
            
            # Show key settings
            print(f"\n📊 Configuration Summary:")
            print(f"   Environment: {config.environment}")
            print(f"   Debug Mode: {config.debug}")
            print(f"   OpenAI Model: {config.api.openai_model}")
            print(f"   Batch Size: {config.processing.batch_size}")
            print(f"   Max Concurrent: {config.processing.max_concurrent_requests}")
            print(f"   Caching: {'Enabled' if config.processing.enable_caching else 'Disabled'}")
            print(f"   Logging Level: {config.logging.level}")
            
        else:
            print("❌ Configuration validation failed!")
            print("\n🚨 Issues found:")
            for i, issue in enumerate(issues, 1):
                print(f"   {i}. {issue}")
            
            print(f"\n💡 Fix these issues in: {args.config_dir}/{args.environment}.yml")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        sys.exit(1)

def show_config(args):
    """Show current configuration"""
    try:
        config_manager = ConfigManager(args.config_dir)
        config = config_manager.load_config(args.environment)
        
        if args.section:
            # Show specific section
            if hasattr(config, args.section):
                section_obj = getattr(config, args.section)
                if hasattr(section_obj, '__dataclass_fields__'):
                    print(f"📋 {args.section.upper()} Configuration:")
                    for field_name in section_obj.__dataclass_fields__:
                        value = getattr(section_obj, field_name)
                        print(f"   {field_name}: {value}")
                else:
                    print(f"📋 {args.section}: {section_obj}")
            else:
                print(f"❌ Unknown configuration section: {args.section}")
                return
        else:
            # Show full configuration
            config_dict = config.to_dict()
            
            if args.format == 'json':
                print(json.dumps(config_dict, indent=2))
            elif args.format == 'yaml':
                print(yaml.dump(config_dict, default_flow_style=False, indent=2))
            else:
                # Pretty formatted output
                print(f"📋 Configuration for {config.environment}:")
                print("=" * 50)
                
                for section_name, section_data in config_dict.items():
                    if isinstance(section_data, dict):
                        print(f"\n🔧 {section_name.upper()}:")
                        for key, value in section_data.items():
                            print(f"   {key}: {value}")
                    else:
                        print(f"\n📝 {section_name}: {section_data}")
    
    except Exception as e:
        print(f"❌ Failed to show configuration: {e}")
        sys.exit(1)

def update_config(args):
    """Update configuration setting"""
    try:
        config_manager = ConfigManager(args.config_dir)
        config = config_manager.load_config(args.environment)
        
        # Parse the key path (e.g., "api.openai_model")
        key_parts = args.key.split('.')
        
        if len(key_parts) == 1:
            # Top-level setting
            if hasattr(config, key_parts[0]):
                setattr(config, key_parts[0], args.value)
            else:
                print(f"❌ Unknown configuration key: {args.key}")
                return
        elif len(key_parts) == 2:
            # Nested setting
            section_name, field_name = key_parts
            if hasattr(config, section_name):
                section_obj = getattr(config, section_name)
                if hasattr(section_obj, field_name):
                    # Try to convert value to appropriate type
                    old_value = getattr(section_obj, field_name)
                    if isinstance(old_value, bool):
                        new_value = args.value.lower() in ['true', '1', 'yes', 'on']
                    elif isinstance(old_value, int):
                        new_value = int(args.value)
                    elif isinstance(old_value, float):
                        new_value = float(args.value)
                    else:
                        new_value = args.value
                    
                    setattr(section_obj, field_name, new_value)
                    
                    print(f"✅ Updated {args.key}: {old_value} → {new_value}")
                else:
                    print(f"❌ Unknown configuration field: {args.key}")
                    return
            else:
                print(f"❌ Unknown configuration section: {section_name}")
                return
        else:
            print(f"❌ Invalid key format: {args.key}. Use 'section.field' format.")
            return
        
        # Save updated configuration
        config_file = Path(args.config_dir) / f"{args.environment}.yml"
        config.save_to_file(config_file)
        
        print(f"💾 Configuration saved to {config_file}")
        
        # Validate after update
        issues = config.validate()
        if issues:
            print("⚠️  Warning: Configuration issues detected after update:")
            for issue in issues:
                print(f"   - {issue}")
    
    except Exception as e:
        print(f"❌ Failed to update configuration: {e}")
        sys.exit(1)

def copy_config(args):
    """Copy configuration between environments"""
    try:
        config_manager = ConfigManager(args.config_dir)
        
        # Load source configuration
        source_config = config_manager.load_config(args.source)
        
        # Update environment name
        source_config.environment = args.target
        
        # Save as target environment
        target_file = Path(args.config_dir) / f"{args.target}.yml"
        source_config.save_to_file(target_file)
        
        print(f"✅ Copied configuration from '{args.source}' to '{args.target}'")
        print(f"💾 Saved to: {target_file}")
        
        # Validate new configuration
        issues = source_config.validate()
        if issues:
            print("⚠️  Warning: Issues detected in copied configuration:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ New configuration is valid")
    
    except Exception as e:
        print(f"❌ Failed to copy configuration: {e}")
        sys.exit(1)

def list_configs(args):
    """List available configurations"""
    config_dir = Path(args.config_dir)
    
    if not config_dir.exists():
        print(f"❌ Configuration directory not found: {config_dir}")
        print("💡 Run 'python cli_config.py init' to create configuration files")
        return
    
    config_files = list(config_dir.glob("*.yml")) + list(config_dir.glob("*.json"))
    
    if not config_files:
        print(f"📁 No configuration files found in {config_dir}")
        print("💡 Run 'python cli_config.py init' to create configuration files")
        return
    
    print(f"📁 Configuration files in {config_dir}:")
    print("=" * 40)
    
    current_env = args.environment or "development"
    
    for config_file in sorted(config_files):
        env_name = config_file.stem
        is_current = env_name == current_env
        status_icon = "👉" if is_current else "  "
        
        try:
            # Try to load and validate
            config_manager = ConfigManager(args.config_dir)
            config = config_manager.load_config(env_name)
            issues = config.validate()
            
            validation_status = "✅" if not issues else f"⚠️  ({len(issues)} issues)"
            
            print(f"{status_icon} {env_name:<15} {config_file.name:<20} {validation_status}")
            
        except Exception as e:
            print(f"{status_icon} {env_name:<15} {config_file.name:<20} ❌ (invalid)")

def test_config(args):
    """Test configuration with actual services"""
    print(f"🧪 Testing configuration for environment: {args.environment}")
    
    try:
        config_manager = ConfigManager(args.config_dir)
        config = config_manager.load_config(args.environment)
        
        # Test logging setup
        print("1️⃣ Testing logging configuration...")
        try:
            logger = config.setup_logging()
            logger.info("Test log message")
            print("   ✅ Logging configured successfully")
        except Exception as e:
            print(f"   ❌ Logging test failed: {e}")
        
        # Test API keys
        print("2️⃣ Testing API keys...")
        if config.api.openai_api_key:
            print("   ✅ OpenAI API key configured")
            
            # Test OpenAI connection (optional)
            if args.full:
                try:
                    from utils.api_client import RobustOpenAIClient
                    client = RobustOpenAIClient(api_key=config.api.openai_api_key)
                    # Simple test call
                    result = client.complete("Test", max_tokens=5)
                    if result['success']:
                        print("   ✅ OpenAI API connection successful")
                    else:
                        print(f"   ⚠️  OpenAI API test failed: {result.get('error', 'Unknown error')}")
                except ImportError:
                    print("   ⚠️  OpenAI client not available for testing")
                except Exception as e:
                    print(f"   ⚠️  OpenAI API test failed: {e}")
        else:
            print("   ⚠️  OpenAI API key not configured")
        
        if config.api.serpapi_api_key:
            print("   ✅ SerpAPI key configured")
            
            # Test SerpAPI connection (optional)
            if args.full:
                try:
                    from utils.api_client import RobustSerpAPIClient
                    client = RobustSerpAPIClient(api_key=config.api.serpapi_api_key)
                    result = client.search("test query", num=1)
                    if result['success']:
                        print("   ✅ SerpAPI connection successful")
                    else:
                        print(f"   ⚠️  SerpAPI test failed: {result.get('error', 'Unknown error')}")
                except ImportError:
                    print("   ⚠️  SerpAPI client not available for testing")
                except Exception as e:
                    print(f"   ⚠️  SerpAPI test failed: {e}")
        else:
            print("   ⚠️  SerpAPI key not configured")
        
        # Test directory structure
        print("3️⃣ Testing directory structure...")
        
        # Templates directory
        templates_dir = Path(config.scoring.templates_directory)
        if templates_dir.exists():
            template_count = len(list(templates_dir.glob("*.txt")))
            print(f"   ✅ Templates directory exists ({template_count} templates)")
        else:
            print(f"   ⚠️  Templates directory not found: {templates_dir}")
        
        # Temp directory
        temp_dir = Path(config.processing.temp_directory)
        temp_dir.mkdir(parents=True, exist_ok=True)
        print(f"   ✅ Temp directory ready: {temp_dir}")
        
        # Logs directory  
        logs_dir = Path(config.logging.file_path).parent
        logs_dir.mkdir(parents=True, exist_ok=True)
        print(f"   ✅ Logs directory ready: {logs_dir}")
        
        print("\n🎉 Configuration test completed!")
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='Configuration Management CLI for Recursor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli_config.py init                                    # Initialize configuration
  python cli_config.py validate --env production              # Validate production config
  python cli_config.py show --section api                     # Show API configuration
  python cli_config.py update api.openai_model gpt-4          # Update OpenAI model
  python cli_config.py copy development testing               # Copy dev config to testing
  python cli_config.py test --env production --full           # Full configuration test
        """
    )
    
    # Global options
    parser.add_argument('--config-dir', default='config', help='Configuration directory')
    parser.add_argument('--env', '--environment', dest='environment', 
                       default=None, help='Environment name (development, production, etc.)')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init command
    init_cmd = subparsers.add_parser('init', help='Initialize configuration files')
    
    # Validate command
    validate_cmd = subparsers.add_parser('validate', help='Validate configuration')
    
    # Show command
    show_cmd = subparsers.add_parser('show', help='Show configuration')
    show_cmd.add_argument('--section', help='Show specific configuration section')
    show_cmd.add_argument('--format', choices=['pretty', 'json', 'yaml'], default='pretty',
                         help='Output format')
    
    # Update command
    update_cmd = subparsers.add_parser('update', help='Update configuration setting')
    update_cmd.add_argument('key', help='Configuration key (e.g., api.openai_model)')
    update_cmd.add_argument('value', help='New value')
    
    # Copy command
    copy_cmd = subparsers.add_parser('copy', help='Copy configuration between environments')
    copy_cmd.add_argument('source', help='Source environment')
    copy_cmd.add_argument('target', help='Target environment')
    
    # List command
    list_cmd = subparsers.add_parser('list', help='List available configurations')
    
    # Test command
    test_cmd = subparsers.add_parser('test', help='Test configuration')
    test_cmd.add_argument('--full', action='store_true', help='Run full tests including API calls')
    
    args = parser.parse_args()
    
    # Set default environment if not specified
    if not args.environment:
        args.environment = 'development'
    
    # Route commands
    if args.command == 'init':
        init_config(args)
    elif args.command == 'validate':
        validate_config(args)
    elif args.command == 'show':
        show_config(args)
    elif args.command == 'update':
        update_config(args)
    elif args.command == 'copy':
        copy_config(args)
    elif args.command == 'list':
        list_configs(args)
    elif args.command == 'test':
        test_config(args)
    else:
        parser.print_help()
        print("\n❌ Error: Please specify a command")
        sys.exit(1)

if __name__ == "__main__":
    main()
