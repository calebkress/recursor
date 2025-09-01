#!/usr/bin/env python3
"""
Prompt template renderer using Jinja2 with versioning support
"""

import os
from typing import Dict, Any, Optional
from jinja2 import Template
from pathlib import Path

class PromptRenderer:
    """Renders prompt templates with variable substitution"""
    
    def __init__(self, templates_dir: str = "prompts"):
        self.templates_dir = templates_dir
    
    def render_template(self, template_name: str, variables: Dict[str, Any]) -> str:
        """Render a template with the given variables
        
        Args:
            template_name: Name of template file (e.g., 'recurly_template.txt')
            variables: Dict of variables to substitute in template
            
        Returns:
            Rendered prompt string
        """
        template_path = os.path.join(self.templates_dir, template_name)
        
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        # Load template content
        with open(template_path, 'r') as f:
            template_content = f.read()
        
        # Create Jinja2 template and render
        template = Template(template_content)
        rendered = template.render(**variables)
        
        return rendered
    
    def render_recurly_template(self, company: str, enriched_data: str, version: Optional[str] = None) -> str:
        """Convenience method for Recurly scoring template with version support
        
        Args:
            company: Company name
            enriched_data: Enriched research data as formatted string
            version: Optional version suffix (e.g., 'v2' for recurly_template_v2.txt)
            
        Returns:
            Rendered Recurly scoring prompt
        """
        variables = {
            'company': company,
            'enriched_data': enriched_data
        }
        
        template_name = 'recurly_template.txt'
        if version:
            # Support versioned templates like recurly_template_v2.txt
            template_name = f'recurly_template_{version}.txt'
        
        return self.render_template(template_name, variables)
    
    def render_with_version_manager(self, version_id: str, variables: Dict[str, Any]) -> str:
        """Render template using version manager
        
        Args:
            version_id: Version ID from PromptVersionManager
            variables: Template variables
            
        Returns:
            Rendered prompt
        """
        from .prompt_manager import PromptVersionManager
        
        manager = PromptVersionManager(self.templates_dir)
        version = manager.get_prompt_version(version_id)
        
        if not version:
            raise ValueError(f"Version {version_id} not found")
        
        if not version.active:
            raise ValueError(f"Version {version_id} is inactive")
        
        return self.render_template(version.template_file, variables)

# Test function
def test_renderer():
    """Test the prompt renderer"""
    renderer = PromptRenderer()
    
    # Sample enriched data
    sample_data = """
HIRING SIGNALS:
- Shopify is hiring Senior Software Engineers for billing systems
- Looking for Product Managers with subscription experience
- Recent job postings mention "recurring revenue optimization"

TECH STACK:
- Uses Ruby on Rails, React, GraphQL
- Built on AWS infrastructure
- Has complex billing integrations

NEWS MENTIONS:
- Shopify Plus growing rapidly in enterprise segment
- Recent focus on subscription commerce features
- Expanding internationally, dealing with tax complexity
    """
    
    try:
        prompt = renderer.render_recurly_template("Shopify", sample_data.strip())
        print("✅ Prompt renderer working!")
        print(f"Generated prompt length: {len(prompt)} characters")
        return True
    except Exception as e:
        print(f"❌ Renderer Error: {e}")
        return False

if __name__ == "__main__":
    test_renderer()
