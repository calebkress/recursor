#!/usr/bin/env python3
"""
MVP Demo Script for Recursor Lead Enrichment and Scoring Pipeline

Usage: python mvp_demo.py
"""

import csv
import json
import os
from typing import List, Dict

# Import our modules
from enrich.serp_api import LeadEnricher
from score.scorer import LeadScorer

def load_leads_from_csv(csv_path: str) -> List[str]:
    """Load company names from CSV file
    
    Args:
        csv_path: Path to CSV file with company names
        
    Returns:
        List of company names
    """
    companies = []
    with open(csv_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            companies.append(row['company'])
    return companies

def enrich_companies(companies: List[str]) -> List[Dict]:
    """Enrich all companies with web research data
    
    Args:
        companies: List of company names
        
    Returns:
        List of enriched company data
    """
    enricher = LeadEnricher()
    enriched_data = []
    
    print(f"🔍 Enriching {len(companies)} companies...")
    
    for company in companies:
        print(f"  Researching {company}...")
        try:
            data = enricher.enrich_company(company)
            enriched_data.append(data)
        except Exception as e:
            print(f"  ❌ Error enriching {company}: {e}")
            # Add empty data so we can still attempt scoring
            enriched_data.append({
                "company": company,
                "hiring_signals": [],
                "tech_stack": [],
                "news_mentions": []
            })
    
    print(f"✅ Enrichment complete!")
    return enriched_data

def score_companies(enriched_data: List[Dict]) -> List[Dict]:
    """Score all enriched companies
    
    Args:
        enriched_data: List of enriched company data
        
    Returns:
        List of scored companies
    """
    scorer = LeadScorer()
    scored_data = []
    
    print(f"🧠 Scoring {len(enriched_data)} companies...")
    
    for data in enriched_data:
        company = data['company']
        print(f"  Scoring {company}...")
        try:
            result = scorer.score_company(company, data)
            scored_data.append(result)
        except Exception as e:
            print(f"  ❌ Error scoring {company}: {e}")
            scored_data.append({
                "company": company,
                "score": 0,
                "error": str(e)
            })
    
    print(f"✅ Scoring complete!")
    return scored_data

def save_results(data: List[Dict], output_path: str):
    """Save results to JSON file
    
    Args:
        data: Results data
        output_path: Path to save JSON file
    """
    with open(output_path, 'w') as file:
        json.dump(data, file, indent=2)
    print(f"💾 Results saved to {output_path}")

def print_summary(scored_data: List[Dict]):
    """Print a summary of the results
    
    Args:
        scored_data: List of scored companies
    """
    print("\\n🎯 SCORING SUMMARY:")
    print("=" * 50)
    
    # Sort by score (descending)
    sorted_data = sorted(scored_data, key=lambda x: x.get('score', 0), reverse=True)
    
    for result in sorted_data:
        company = result.get('company', 'Unknown')
        score = result.get('score', 0)
        priority = result.get('priority', 'N/A')
        justification = result.get('justification', 'No justification provided')
        
        print(f"\\n{company}: {score}/100 ({priority} Priority)")
        print(f"  {justification}")
        
        if 'summary' in result and result['summary']:
            print("  Key insights:")
            for insight in result['summary']:
                print(f"    • {insight}")

def main():
    """Run the full MVP pipeline"""
    print("🚀 Recursor MVP Demo - Lead Enrichment & Scoring Pipeline")
    print("=" * 60)
    
    # Configuration
    input_csv = "data/sample_leads.csv"
    output_json = "data/mvp_results.json"
    
    try:
        # Step 1: Load leads
        print("\\n📄 Step 1: Loading leads from CSV...")
        companies = load_leads_from_csv(input_csv)
        print(f"Loaded {len(companies)} companies: {', '.join(companies)}")
        
        # Step 2: Enrich companies
        print("\\n🔍 Step 2: Enriching companies with web research...")
        enriched_data = enrich_companies(companies)
        
        # Step 3: Score companies
        print("\\n🧠 Step 3: Scoring companies with AI...")
        scored_data = score_companies(enriched_data)
        
        # Step 4: Save results
        print("\\n💾 Step 4: Saving results...")
        save_results(scored_data, output_json)
        
        # Step 5: Show summary
        print_summary(scored_data)
        
        print("\\n🎉 MVP Demo Complete!")
        print(f"Full results available in: {output_json}")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
