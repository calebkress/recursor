#!/usr/bin/env python3
"""
CLI for managing prompt versions and A/B tests
"""

import argparse
import json
import sys
from pathlib import Path
from prompts.prompt_manager import PromptVersionManager

def list_versions(manager: PromptVersionManager, args):
    """List all prompt versions"""
    versions = manager.list_prompt_versions(args.name)
    
    if not versions:
        print("No prompt versions found")
        return
    
    print(f"\n📝 Prompt Versions ({len(versions)}):")
    print("-" * 50)
    for version in versions:
        status = "✅ Active" if version.active else "❌ Inactive" 
        print(f"{version.name} {version.version} - {status}")
        print(f"  ID: {version.id}")
        print(f"  File: {version.template_file}")
        print(f"  Description: {version.description}")
        print(f"  Created: {version.created_at} by {version.created_by}")
        if version.performance_metrics:
            print(f"  Metrics: {version.performance_metrics}")
        print()

def create_version(manager: PromptVersionManager, args):
    """Create a new prompt version"""
    version_id = manager.create_prompt_version(
        name=args.name,
        template_file=args.file,
        description=args.description,
        variables=args.variables.split(',') if args.variables else None,
        created_by=args.author
    )
    print(f"Created version {version_id}")

def create_ab_test(manager: PromptVersionManager, args):
    """Create a new A/B test"""
    versions = args.versions.split(',')
    
    # Parse traffic split if provided
    traffic_split = None
    if args.traffic_split:
        try:
            # Expect format like "v1:0.3,v2:0.7"
            splits = {}
            for split in args.traffic_split.split(','):
                version_id, percentage = split.split(':')
                splits[version_id.strip()] = float(percentage)
            traffic_split = splits
        except Exception as e:
            print(f"Error parsing traffic split: {e}")
            print("Format should be: version1:0.5,version2:0.5")
            return
    
    try:
        test_id = manager.create_ab_test(
            name=args.name,
            description=args.description,
            prompt_versions=versions,
            traffic_split=traffic_split
        )
        print(f"Created A/B test {test_id}")
    except ValueError as e:
        print(f"Error creating A/B test: {e}")

def list_ab_tests(manager: PromptVersionManager, args):
    """List A/B tests"""
    active_tests = manager.get_active_ab_tests()
    all_tests = manager.ab_tests
    
    print(f"\n🧪 A/B Tests ({len(active_tests)} active, {len(all_tests)} total):")
    print("-" * 50)
    
    for test_id, test in all_tests.items():
        status = "✅ Active" if test.active else "❌ Stopped"
        print(f"{test.name} - {status}")
        print(f"  ID: {test_id}")
        print(f"  Description: {test.description}")
        print(f"  Versions: {len(test.prompt_versions)}")
        print(f"  Traffic Split: {test.traffic_split}")
        print(f"  Start Date: {test.start_date}")
        if test.end_date:
            print(f"  End Date: {test.end_date}")
        
        # Show results if available
        if test_id in manager.results:
            total_results = sum(len(results) for results in manager.results[test_id].values())
            print(f"  Results: {total_results} samples")
        print()

def analyze_test(manager: PromptVersionManager, args):
    """Analyze A/B test results"""
    analysis = manager.analyze_ab_test_results(args.test_id)
    
    if 'error' in analysis:
        print(f"Error: {analysis['error']}")
        return
    
    print(f"\n📊 A/B Test Analysis: {args.test_id}")
    print("=" * 60)
    
    # Print version results
    if analysis['versions']:
        print("\n📝 Version Performance:")
        for version_name, metrics in analysis['versions'].items():
            print(f"\n{version_name}:")
            print(f"  Sample Size: {metrics['sample_size']}")
            print(f"  Average Score: {metrics['avg_score']:.1f}/100")
            print(f"  Score Range: {metrics['min_score']}-{metrics['max_score']}")
    
    # Print summary
    if analysis['summary']:
        summary = analysis['summary']
        print(f"\n📈 Overall Summary:")
        print(f"  Total Samples: {summary['total_samples']}")
        print(f"  Overall Average: {summary['overall_avg']:.1f}/100")
        if summary['best_version']:
            print(f"  Best Performing: {summary['best_version']}")

def stop_test(manager: PromptVersionManager, args):
    """Stop an A/B test"""
    manager.stop_ab_test(args.test_id)
    print(f"Stopped A/B test {args.test_id}")

def run_test_scoring(manager: PromptVersionManager, args):
    """Run a quick test scoring with A/B test"""
    from score.scorer import LeadScorer
    from enrich.serp_api import LeadEnricher
    
    # Get test companies
    companies = args.companies.split(',')
    
    print(f"Running test scoring for A/B test {args.test_id}")
    print(f"Companies: {companies}")
    
    # Initialize components with A/B test
    enricher = LeadEnricher()
    scorer = LeadScorer(ab_test_id=args.test_id)
    
    for company in companies:
        print(f"\nTesting {company}...")
        
        # Enrich
        enriched = enricher.enrich_company(company.strip())
        
        # Score
        result = scorer.score_company(company.strip(), enriched)
        
        # Print result
        print(f"  Score: {result.get('score', 'N/A')}")
        print(f"  Version: {result.get('prompt_version_id', 'default')}")
        if 'key_signals' in result:
            print(f"  Key Signals: {result['key_signals']}")

def main():
    parser = argparse.ArgumentParser(
        description='Manage prompt versions and A/B tests',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List versions command
    list_cmd = subparsers.add_parser('list-versions', help='List prompt versions')
    list_cmd.add_argument('--name', help='Filter by prompt name')
    
    # Create version command  
    create_cmd = subparsers.add_parser('create-version', help='Create new prompt version')
    create_cmd.add_argument('name', help='Prompt name')
    create_cmd.add_argument('file', help='Template file name')
    create_cmd.add_argument('--description', default='', help='Version description')
    create_cmd.add_argument('--variables', help='Comma-separated variable names')
    create_cmd.add_argument('--author', default='user', help='Author name')
    
    # Create A/B test command
    ab_create_cmd = subparsers.add_parser('create-ab-test', help='Create A/B test')
    ab_create_cmd.add_argument('name', help='Test name')
    ab_create_cmd.add_argument('versions', help='Comma-separated version IDs')
    ab_create_cmd.add_argument('--description', default='', help='Test description')
    ab_create_cmd.add_argument('--traffic-split', help='Traffic split (e.g., v1:0.5,v2:0.5)')
    
    # List A/B tests command
    ab_list_cmd = subparsers.add_parser('list-ab-tests', help='List A/B tests')
    
    # Analyze test command
    analyze_cmd = subparsers.add_parser('analyze-test', help='Analyze A/B test results')
    analyze_cmd.add_argument('test_id', help='Test ID to analyze')
    
    # Stop test command
    stop_cmd = subparsers.add_parser('stop-test', help='Stop A/B test')
    stop_cmd.add_argument('test_id', help='Test ID to stop')
    
    # Run test scoring command
    test_score_cmd = subparsers.add_parser('test-scoring', help='Run test scoring with A/B test')
    test_score_cmd.add_argument('test_id', help='A/B test ID to use')
    test_score_cmd.add_argument('companies', help='Comma-separated company names')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize manager
    manager = PromptVersionManager()
    
    # Route commands
    if args.command == 'list-versions':
        list_versions(manager, args)
    elif args.command == 'create-version':
        create_version(manager, args)
    elif args.command == 'create-ab-test':
        create_ab_test(manager, args)
    elif args.command == 'list-ab-tests':
        list_ab_tests(manager, args)
    elif args.command == 'analyze-test':
        analyze_test(manager, args)
    elif args.command == 'stop-test':
        stop_test(manager, args)
    elif args.command == 'test-scoring':
        run_test_scoring(manager, args)

if __name__ == "__main__":
    main()
