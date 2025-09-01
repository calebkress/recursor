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
    
    # Load companies
    companies = load_csv(args.input)
    print(f"Loaded {len(companies)} companies")
    
    # Initialize enricher
    enricher = LeadEnricher()
    enriched_data = []
    
    # Enrich each company
    for i, company in enumerate(companies, 1):
        print(f"  [{i}/{len(companies)}] Researching {company}...")
        try:
            data = enricher.enrich_company(company)
            enriched_data.append(data)
        except Exception as e:
            print(f"    ⚠️  Warning: Error enriching {company}: {e}")
            # Add minimal data to continue pipeline
            enriched_data.append({
                "company": company,
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
            result = scorer.score_company(company, data)
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

def full_run_mode(args):
    """Run the complete pipeline: enrich + score"""
    print(f"🚀 Running full pipeline from {args.input}...")
    
    # Step 1: Load and enrich
    companies = load_csv(args.input)
    print(f"Loaded {len(companies)} companies")
    
    enricher = LeadEnricher()
    enriched_data = []
    
    print("\n🔍 Step 1: Enrichment")
    for i, company in enumerate(companies, 1):
        print(f"  [{i}/{len(companies)}] Researching {company}...")
        try:
            data = enricher.enrich_company(company)
            enriched_data.append(data)
        except Exception as e:
            print(f"    ⚠️  Warning: {e}")
            enriched_data.append({
                "company": company,
                "hiring_signals": [],
                "tech_stack": [],
                "news_mentions": [],
                "error": str(e)
            })
    
    # Step 2: Score
    scorer = LeadScorer(model=args.model)
    scored_data = []
    
    print("\n🧠 Step 2: Scoring")
    for i, data in enumerate(enriched_data, 1):
        company = data['company']
        print(f"  [{i}/{len(enriched_data)}] Scoring {company}...")
        try:
            result = scorer.score_company(company, data)
            scored_data.append(result)
        except Exception as e:
            print(f"    ⚠️  Warning: {e}")
            scored_data.append({
                "company": company,
                "score": 0,
                "error": str(e)
            })
    
    # Save final results
    save_json(args.output, scored_data)
    
    # Print summary
    print_score_summary(scored_data)
    print(f"\n🎉 Full pipeline complete! Results saved to {args.output}")

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
  python cli.py full-run --input data/leads.csv --output data/scored.json
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
    score_parser.add_argument('--model', default='gpt-3.5-turbo', help='OpenAI model to use')
    
    # Full-run command
    full_parser = subparsers.add_parser('full-run', help='Run complete pipeline')
    full_parser.add_argument('--input', required=True, help='Input CSV file with companies')
    full_parser.add_argument('--output', required=True, help='Output JSON file for final results')
    full_parser.add_argument('--model', default='gpt-3.5-turbo', help='OpenAI model to use')
    
    args = parser.parse_args()
    
    # Route to appropriate function
    if args.command == 'enrich':
        enrich_mode(args)
    elif args.command == 'score':
        score_mode(args)
    elif args.command == 'full-run':
        full_run_mode(args)
    else:
        parser.print_help()
        print("\n❌ Error: Please specify a command (enrich, score, or full-run)")
        sys.exit(1)

if __name__ == '__main__':
    main()
