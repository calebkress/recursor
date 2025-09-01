#!/usr/bin/env python3
"""
Prompt versioning and A/B testing system for Recursor
"""

import os
import json
import random
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import uuid

@dataclass
class PromptVersion:
    """Represents a single version of a prompt"""
    id: str
    name: str
    version: str
    description: str
    template_file: str
    variables: List[str]
    created_at: str
    created_by: str
    active: bool = True
    performance_metrics: Dict[str, float] = None
    
    def __post_init__(self):
        if self.performance_metrics is None:
            self.performance_metrics = {}

@dataclass
class ABTestConfig:
    """Configuration for A/B testing"""
    name: str
    description: str
    prompt_versions: List[str]  # List of prompt version IDs
    traffic_split: Dict[str, float]  # version_id -> percentage (0.0-1.0)
    start_date: str
    end_date: Optional[str] = None
    active: bool = True
    results: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.results is None:
            self.results = {}

class PromptVersionManager:
    """Manages prompt versions and A/B testing"""
    
    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = Path(prompts_dir)
        self.versions_file = self.prompts_dir / "versions.json"
        self.ab_tests_file = self.prompts_dir / "ab_tests.json"
        self.results_file = self.prompts_dir / "test_results.json"
        
        # Ensure directory exists
        self.prompts_dir.mkdir(exist_ok=True)
        
        # Load existing data
        self.versions = self._load_versions()
        self.ab_tests = self._load_ab_tests()
        self.results = self._load_results()
    
    def _load_versions(self) -> Dict[str, PromptVersion]:
        """Load prompt versions from file"""
        if not self.versions_file.exists():
            return {}
        
        try:
            with open(self.versions_file, 'r') as f:
                data = json.load(f)
            
            versions = {}
            for version_id, version_data in data.items():
                versions[version_id] = PromptVersion(**version_data)
            
            return versions
        except Exception as e:
            print(f"Error loading versions: {e}")
            return {}
    
    def _save_versions(self):
        """Save prompt versions to file"""
        data = {}
        for version_id, version in self.versions.items():
            data[version_id] = asdict(version)
        
        with open(self.versions_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_ab_tests(self) -> Dict[str, ABTestConfig]:
        """Load A/B test configurations"""
        if not self.ab_tests_file.exists():
            return {}
        
        try:
            with open(self.ab_tests_file, 'r') as f:
                data = json.load(f)
            
            ab_tests = {}
            for test_id, test_data in data.items():
                ab_tests[test_id] = ABTestConfig(**test_data)
            
            return ab_tests
        except Exception as e:
            print(f"Error loading A/B tests: {e}")
            return {}
    
    def _save_ab_tests(self):
        """Save A/B test configurations"""
        data = {}
        for test_id, test in self.ab_tests.items():
            data[test_id] = asdict(test)
        
        with open(self.ab_tests_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_results(self) -> Dict[str, Any]:
        """Load test results"""
        if not self.results_file.exists():
            return {}
        
        try:
            with open(self.results_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading results: {e}")
            return {}
    
    def _save_results(self):
        """Save test results"""
        with open(self.results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
    
    def create_prompt_version(
        self, 
        name: str, 
        template_file: str, 
        description: str = "",
        variables: Optional[List[str]] = None,
        created_by: str = "system"
    ) -> str:
        """Create a new prompt version"""
        
        # Generate unique ID and version number
        version_id = str(uuid.uuid4())
        existing_versions = [v for v in self.versions.values() if v.name == name]
        version_number = f"v{len(existing_versions) + 1}.0"
        
        # Default variables
        if variables is None:
            variables = ["company", "enriched_data"]
        
        version = PromptVersion(
            id=version_id,
            name=name,
            version=version_number,
            description=description,
            template_file=template_file,
            variables=variables,
            created_at=datetime.now().isoformat(),
            created_by=created_by
        )
        
        self.versions[version_id] = version
        self._save_versions()
        
        print(f"Created prompt version: {name} {version_number} (ID: {version_id})")
        return version_id
    
    def get_prompt_version(self, version_id: str) -> Optional[PromptVersion]:
        """Get a specific prompt version"""
        return self.versions.get(version_id)
    
    def list_prompt_versions(self, name: Optional[str] = None) -> List[PromptVersion]:
        """List all prompt versions, optionally filtered by name"""
        versions = list(self.versions.values())
        if name:
            versions = [v for v in versions if v.name == name]
        
        return sorted(versions, key=lambda v: v.created_at, reverse=True)
    
    def deactivate_version(self, version_id: str):
        """Deactivate a prompt version"""
        if version_id in self.versions:
            self.versions[version_id].active = False
            self._save_versions()
            print(f"Deactivated version {version_id}")
    
    def create_ab_test(
        self,
        name: str,
        description: str,
        prompt_versions: List[str],
        traffic_split: Optional[Dict[str, float]] = None
    ) -> str:
        """Create a new A/B test"""
        
        # Validate prompt versions exist
        for version_id in prompt_versions:
            if version_id not in self.versions:
                raise ValueError(f"Prompt version {version_id} not found")
        
        # Default equal traffic split
        if traffic_split is None:
            split_percent = 1.0 / len(prompt_versions)
            traffic_split = {v_id: split_percent for v_id in prompt_versions}
        
        # Validate traffic split sums to 1.0
        total_traffic = sum(traffic_split.values())
        if abs(total_traffic - 1.0) > 0.001:
            raise ValueError(f"Traffic split must sum to 1.0, got {total_traffic}")
        
        test_id = str(uuid.uuid4())
        
        ab_test = ABTestConfig(
            name=name,
            description=description,
            prompt_versions=prompt_versions,
            traffic_split=traffic_split,
            start_date=datetime.now().isoformat()
        )
        
        self.ab_tests[test_id] = ab_test
        self._save_ab_tests()
        
        print(f"Created A/B test: {name} (ID: {test_id})")
        print(f"Testing versions: {prompt_versions}")
        print(f"Traffic split: {traffic_split}")
        
        return test_id
    
    def get_prompt_for_ab_test(self, test_id: str) -> Optional[str]:
        """Get a prompt version ID based on A/B test traffic split"""
        if test_id not in self.ab_tests:
            return None
        
        test = self.ab_tests[test_id]
        if not test.active:
            return None
        
        # Use weighted random selection
        versions = list(test.traffic_split.keys())
        weights = list(test.traffic_split.values())
        
        return random.choices(versions, weights=weights)[0]
    
    def record_test_result(
        self,
        test_id: str,
        version_id: str,
        company: str,
        result: Dict[str, Any]
    ):
        """Record a result from an A/B test"""
        if test_id not in self.results:
            self.results[test_id] = {}
        
        if version_id not in self.results[test_id]:
            self.results[test_id][version_id] = []
        
        self.results[test_id][version_id].append({
            "company": company,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_results()
    
    def analyze_ab_test_results(self, test_id: str) -> Dict[str, Any]:
        """Analyze results from an A/B test"""
        if test_id not in self.results:
            return {"error": "No results found for test"}
        
        test_results = self.results[test_id]
        analysis = {
            "test_id": test_id,
            "versions": {},
            "summary": {}
        }
        
        all_scores = []
        
        for version_id, results in test_results.items():
            version = self.get_prompt_version(version_id)
            version_name = f"{version.name} {version.version}" if version else version_id
            
            scores = [r["result"].get("score", 0) for r in results if "score" in r["result"]]
            
            if scores:
                analysis["versions"][version_name] = {
                    "version_id": version_id,
                    "sample_size": len(scores),
                    "avg_score": sum(scores) / len(scores),
                    "min_score": min(scores),
                    "max_score": max(scores),
                    "total_scores": sum(scores)
                }
                all_scores.extend(scores)
        
        # Overall summary
        if all_scores:
            analysis["summary"] = {
                "total_samples": len(all_scores),
                "overall_avg": sum(all_scores) / len(all_scores),
                "best_version": max(analysis["versions"].items(), 
                                  key=lambda x: x[1]["avg_score"])[0] if analysis["versions"] else None
            }
        
        return analysis
    
    def stop_ab_test(self, test_id: str):
        """Stop an A/B test"""
        if test_id in self.ab_tests:
            self.ab_tests[test_id].active = False
            self.ab_tests[test_id].end_date = datetime.now().isoformat()
            self._save_ab_tests()
            print(f"Stopped A/B test {test_id}")
    
    def get_active_ab_tests(self) -> List[ABTestConfig]:
        """Get all active A/B tests"""
        return [test for test in self.ab_tests.values() if test.active]
    
    def print_summary(self):
        """Print a summary of all versions and tests"""
        print("\n📊 Prompt Versioning Summary")
        print("=" * 50)
        
        print(f"\n📝 Prompt Versions ({len(self.versions)}):")
        for version in self.list_prompt_versions():
            status = "✅ Active" if version.active else "❌ Inactive"
            print(f"  {version.name} {version.version} - {status}")
            print(f"    ID: {version.id}")
            print(f"    File: {version.template_file}")
            print(f"    Created: {version.created_at}")
            if version.performance_metrics:
                print(f"    Metrics: {version.performance_metrics}")
            print()
        
        active_tests = self.get_active_ab_tests()
        print(f"\n🧪 A/B Tests ({len(active_tests)} active, {len(self.ab_tests)} total):")
        for test_id, test in self.ab_tests.items():
            status = "✅ Active" if test.active else "❌ Stopped"
            print(f"  {test.name} - {status}")
            print(f"    ID: {test_id}")
            print(f"    Versions: {len(test.prompt_versions)}")
            print(f"    Traffic: {test.traffic_split}")
            if test_id in self.results:
                total_results = sum(len(results) for results in self.results[test_id].values())
                print(f"    Results: {total_results} samples")
            print()

# Example usage and testing
def demo_prompt_versioning():
    """Demonstrate the prompt versioning system"""
    print("🚀 Prompt Versioning Demo")
    print("=" * 40)
    
    # Initialize manager
    manager = PromptVersionManager()
    
    # Create some example prompt versions
    v1_id = manager.create_prompt_version(
        name="recurly_scoring",
        template_file="recurly_template_v1.txt",
        description="Original Recurly scoring template",
        created_by="caleb"
    )
    
    v2_id = manager.create_prompt_version(
        name="recurly_scoring", 
        template_file="recurly_template_v2.txt",
        description="Enhanced template with more specific criteria",
        created_by="caleb"
    )
    
    # Create A/B test
    test_id = manager.create_ab_test(
        name="Recurly Scoring Optimization",
        description="Compare v1 vs v2 scoring accuracy",
        prompt_versions=[v1_id, v2_id],
        traffic_split={v1_id: 0.5, v2_id: 0.5}
    )
    
    # Print summary
    manager.print_summary()
    
    return manager

if __name__ == "__main__":
    demo_prompt_versioning()
