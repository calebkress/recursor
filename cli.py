#!/usr/bin/env python3
"""
Recursor CLI - Lead enrichment and scoring engine

Usage:
  python cli.py enrich --input data/leads.csv --output data/enriched.json
  python cli.py score --input data/enriched.json --output data/scored.json
  python cli.py full-run --input data/leads.csv --output data/scored.json
"""

import argparse
import csv
import json
import sys
from typing import List, Dict, Any
from pathlib import Path

# Import our modules
from enrich.serp_api import LeadEnricher
from score.scorer import LeadScorer
from analysis.lead_clustering import LeadClusterer
import pandas as pd

def load_csv(path: str) -> List[str]:
    """Load company names from CSV file"""
    companies = []
    try:
        with open(path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                companies.append(row['company'])
        return companies
    except FileNotFoundError:
        print(f"❌ Error: Input file '{path}' not found")
        sys.exit(1)
    except KeyError:
        print(f"❌ Error: CSV must have a 'company' column")
        sys.exit(1)

def load_enriched_json(path: str) -> List[Dict]:
    """Load enriched data from JSON file"""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: Input file '{path}' not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in '{path}': {e}")
        sys.exit(1)

def save_json(path: str, data: List[Dict]):
    """Save data to JSON file"""
    # Create directory if it doesn't exist
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"💾 Saved results to {path}")

def enrich_mode(args):
    """Enrich companies from CSV and save to JSON"""
    print(f"🔍 Enriching leads from {args.input}...")
    
    # Load CSV with pandas to support domain column
    try:
        leads_df = pd.read_csv(args.input)
        print(f"Loaded {len(leads_df)} companies")
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        sys.exit(1)
    
    # Initialize enricher
    enricher = LeadEnricher()
    enriched_data = []
    
    # Enrich each company
    for i, row in leads_df.iterrows():
        company = row.get('company', f'Unknown_{i}')
        domain = row.get('domain', '')
        print(f"  [{i+1}/{len(leads_df)}] Researching {company}...")
        try:
            data = enricher.enrich_company(company)
            enriched_data.append(data)
        except Exception as e:
            print(f"    ⚠️  Warning: Error enriching {company}: {e}")
            # Add minimal data to continue pipeline
            enriched_data.append({
                "company": company,
                "domain": domain,
                "hiring_signals": [],
                "tech_stack": [],
                "news_mentions": [],
                "error": str(e)
            })
    
    # Save results
    save_json(args.output, enriched_data)
    print(f"✅ Enrichment complete! {len(enriched_data)} companies processed")

def score_mode(args):
    """Score enriched companies and save results"""
    print(f"🧠 Scoring leads from {args.input}...")
    
    # Load enriched data
    enriched_data = load_enriched_json(args.input)
    print(f"Loaded {len(enriched_data)} enriched companies")
    
    # Initialize scorer
    scorer = LeadScorer(model=args.model)
    scored_data = []
    
    # Score each company
    for i, data in enumerate(enriched_data, 1):
        company = data.get('company', f'Unknown_{i}')
        print(f"  [{i}/{len(enriched_data)}] Scoring {company}...")
        try:
            result = scorer.score_lead(data, template_name=getattr(args, 'template', 'recurly_template.txt'))
            scored_data.append(result)
        except Exception as e:
            print(f"    ⚠️  Warning: Error scoring {company}: {e}")
            scored_data.append({
                "company": company,
                "score": 0,
                "error": str(e),
                "breakdown": {},
                "summary": [],
                "justification": f"Error occurred during scoring: {e}",
                "priority": "Low",
                "next_steps": "Review error and retry"
            })
    
    # Save results
    save_json(args.output, scored_data)
    
    # Print summary
    print_score_summary(scored_data)
    print(f"✅ Scoring complete! {len(scored_data)} companies scored")

def cluster_mode(args):
    """Cluster scored leads for analysis"""
    print(f"🔍 Clustering leads from {args.input}...")
    
    # Load scored data
    scored_data = load_enriched_json(args.input)
    print(f"Loaded {len(scored_data)} scored leads")
    
    if len(scored_data) < 3:
        print("⚠️  Need at least 3 leads for clustering")
        return
    
    # Initialize clusterer
    clusterer = LeadClusterer(random_state=getattr(args, 'seed', 42))
    
    # Perform clustering
    method = getattr(args, 'method', 'kmeans')
    print(f"Performing {method} clustering...")
    
    try:
        clusters = clusterer.cluster_leads(
            scored_data, 
            method=method, 
            n_clusters=getattr(args, 'clusters', None)
        )
        
        if not clusters:
            print("❌ No clusters generated")
            return
        
        # Print summary
        clusterer.print_cluster_summary()
        
        # Show detailed insights if requested
        if getattr(args, 'detailed', False):
            print(f"\n{'='*60}")
            print("DETAILED CLUSTER INSIGHTS")
            print(f"{'='*60}")
            
            for cluster_id in sorted(clusters.keys()):
                insights = clusterer.get_cluster_insights(cluster_id)
                cluster_info = insights['cluster_info']
                
                print(f"\n📊 CLUSTER {cluster_id}: {cluster_info['cluster_label']}")
                print(f"{'='*50}")
                
                print(f"Companies ({cluster_info['size']}): {', '.join(cluster_info['companies'])}")
                print(f"Average Score: {cluster_info['avg_score']:.1f}/100")
                print(f"Common Themes: {', '.join(cluster_info['common_themes'][:5])}")
                
                print(f"\n🎯 RECOMMENDATIONS:")
                for i, rec in enumerate(insights['recommendations'], 1):
                    print(f"  {i}. {rec}")
        
        # Export results if requested
        if hasattr(args, 'output') and args.output:
            clusterer.export_clusters(args.output)
            print(f"\n💾 Cluster results exported to {args.output}")
        
        print(f"\n✅ Clustering complete! {len(clusters)} clusters created")
        
    except Exception as e:
        print(f"❌ Error during clustering: {e}")
        sys.exit(1)

def full_run_mode(args):
    """Run the complete pipeline: enrich + score + cluster"""
    print(f"🚀 Running full pipeline from {args.input}...")
    
    try:
        # Step 1: Load and enrich
        leads_df = pd.read_csv(args.input)
        print(f"Loaded {len(leads_df)} companies")
        
        enricher = LeadEnricher()
        enriched_data = []
        
        print("\n🔍 Step 1: Enrichment")
        for i, row in leads_df.iterrows():
            company = row.get('company', f'Unknown_{i}')
            domain = row.get('domain', '')
            print(f"  [{i+1}/{len(leads_df)}] Researching {company}...")
            try:
                data = enricher.enrich_company(company)
                enriched_data.append(data)
            except Exception as e:
                print(f"    ⚠️  Warning: {e}")
                enriched_data.append({
                    "company": company,
                    "domain": domain,
                    "hiring_signals": [],
                    "tech_stack": [],
                    "news_mentions": [],
                    "error": str(e)
                })
        
        # Step 2: Score
        scorer = LeadScorer(model=args.model)
        scored_data = []
        
        print("\n🧠 Step 2: Scoring")
        template_name = getattr(args, 'template', 'recurly_template.txt')
        for i, data in enumerate(enriched_data, 1):
            company = data['company']
            print(f"  [{i}/{len(enriched_data)}] Scoring {company}...")
            try:
                result = scorer.score_lead(data, template_name=template_name)
                scored_data.append(result)
            except Exception as e:
                print(f"    ⚠️  Warning: {e}")
                scored_data.append({
                    "company": company,
                    "score": 0,
                    "error": str(e),
                    "breakdown": {},
                    "summary": [],
                    "justification": f"Error occurred during scoring: {e}",
                    "priority": "Low",
                    "next_steps": "Review error and retry"
                })
        
        # Step 3: Clustering (if requested)
        if getattr(args, 'cluster', False) and len(scored_data) >= 3:
            print("\n🔍 Step 3: Clustering")
            clusterer = LeadClusterer(random_state=42)
            
            method = getattr(args, 'cluster_method', 'kmeans')
            print(f"Clustering {len(scored_data)} leads using {method}...")
            
            try:
                clusters = clusterer.cluster_leads(scored_data, method=method)
                
                if clusters:
                    clusterer.print_cluster_summary()
                    
                    # Save cluster results
                    cluster_output = args.output.replace('.json', '_clusters.json')
                    clusterer.export_clusters(cluster_output)
                    print(f"💾 Cluster analysis saved to: {cluster_output}")
                    
                    # Show top cluster
                    top_cluster = max(clusters.values(), key=lambda x: x.avg_score)
                    print(f"\n🎯 Highest Value Cluster: {top_cluster.cluster_label}")
                    print(f"   Average Score: {top_cluster.avg_score:.1f}/100")
                    print(f"   Companies: {', '.join(top_cluster.companies)}")
            except Exception as e:
                print(f"    ⚠️  Warning: Clustering failed: {e}")
        
        # Save final results
        save_json(args.output, scored_data)
        
        # Print summary
        print_score_summary(scored_data)
        print(f"\n🎉 Full pipeline complete! Results saved to {args.output}")
        
    except Exception as e:
        print(f"❌ Pipeline error: {e}")
        sys.exit(1)

def print_score_summary(scored_data: List[Dict]):
    """Print a summary of scoring results"""
    print("\n🎯 Top Scoring Leads:")
    print("-" * 40)
    
    # Sort by score
    sorted_data = sorted(scored_data, key=lambda x: x.get('score', 0), reverse=True)
    
    for result in sorted_data[:5]:  # Top 5
        company = result.get('company', 'Unknown')
        score = result.get('score', 0)
        priority = result.get('priority', 'N/A')
        print(f"{company}: {score}/100 ({priority} Priority)")

def main():
    parser = argparse.ArgumentParser(
        description='Recursor - Lead enrichment and scoring engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py enrich --input data/leads.csv --output data/enriched.json
  python cli.py score --input data/enriched.json --output data/scored.json  
  python cli.py cluster --input data/scored.json --output data/clusters.json --detailed
  python cli.py full-run --input data/leads.csv --output data/scored.json --cluster
        """
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Enrich command
    enrich_parser = subparsers.add_parser('enrich', help='Enrich leads from CSV')
    enrich_parser.add_argument('--input', required=True, help='Input CSV file with companies')
    enrich_parser.add_argument('--output', required=True, help='Output JSON file for enriched data')
    
    # Score command
    score_parser = subparsers.add_parser('score', help='Score enriched leads')
    score_parser.add_argument('--input', required=True, help='Input JSON file with enriched data')
    score_parser.add_argument('--output', required=True, help='Output JSON file for scored results')
    score_parser.add_argument('--model', choices=['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'], default='gpt-4-turbo', help='OpenAI model to use')
    score_parser.add_argument('--template', default='recurly_template.txt', help='Scoring template file')
    
    # Cluster command
    cluster_parser = subparsers.add_parser('cluster', help='Cluster scored leads for analysis')
    cluster_parser.add_argument('--input', required=True, help='Input JSON file with scored leads')
    cluster_parser.add_argument('--output', help='Output JSON file for cluster results')
    cluster_parser.add_argument('--method', choices=['kmeans', 'hierarchical', 'dbscan'], default='kmeans', help='Clustering method')
    cluster_parser.add_argument('--clusters', type=int, help='Number of clusters (auto-detect if not specified)')
    cluster_parser.add_argument('--detailed', action='store_true', help='Show detailed cluster insights')
    cluster_parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility')
    
    # Full-run command
    full_parser = subparsers.add_parser('full-run', help='Run complete pipeline')
    full_parser.add_argument('--input', required=True, help='Input CSV file with companies')
    full_parser.add_argument('--output', required=True, help='Output JSON file for final results')
    full_parser.add_argument('--model', choices=['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'], default='gpt-4-turbo', help='OpenAI model to use')
    full_parser.add_argument('--template', default='recurly_template.txt', help='Scoring template file')
    full_parser.add_argument('--cluster', action='store_true', help='Include clustering analysis')
    full_parser.add_argument('--cluster-method', choices=['kmeans', 'hierarchical', 'dbscan'], default='kmeans', help='Clustering method')
    
    args = parser.parse_args()
    
    # Route to appropriate function
    if args.command == 'enrich':
        enrich_mode(args)
    elif args.command == 'score':
        score_mode(args)
    elif args.command == 'cluster':
        cluster_mode(args)
    elif args.command == 'full-run':
        full_run_mode(args)
    else:
        parser.print_help()
        print("\n❌ Error: Please specify a command (enrich, score, cluster, or full-run)")
        sys.exit(1)

if __name__ == '__main__':
    main()
