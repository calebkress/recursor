#!/usr/bin/env python3
"""
Sample Data Generator for Recursor
Creates realistic synthetic datasets for testing and demos without API costs
"""

import json
import csv
import random
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid

# Company data for realistic generation
INDUSTRIES = [
    "SaaS", "E-commerce", "Fintech", "Edtech", "Healthtech", 
    "Marketing Tech", "Media", "Gaming", "Productivity", "Security",
    "Analytics", "CRM", "HR Tech", "Real Estate Tech", "Supply Chain"
]

COMPANY_SUFFIXES = [
    "Corp", "Inc", "Labs", "Tech", "Systems", "Solutions", "Platform",
    "Software", "Digital", "Works", "Hub", "Studio", "Ventures", "AI"
]

COMPANY_PREFIXES = [
    "Acme", "Apex", "Beta", "Core", "Data", "Edge", "Flow", "Grid",
    "Hyper", "Infinite", "Jet", "Key", "Logic", "Meta", "Neo", "Omni",
    "Peak", "Quantum", "Rapid", "Smart", "Turbo", "Ultra", "Vertex", 
    "Wave", "Xcel", "Yield", "Zen", "Alpha", "Bridge", "Cloud", "Delta",
    "Echo", "Fusion", "Gamma", "Harbor", "Impact", "Nexus", "Orbit",
    "Prime", "Quest", "Radius", "Sphere", "Titan", "Unity", "Vision"
]

TECH_STACKS = [
    ["React", "Node.js", "PostgreSQL", "AWS"],
    ["Vue.js", "Python", "MySQL", "GCP"],
    ["Angular", "Java", "MongoDB", "Azure"],
    ["Next.js", "TypeScript", "Redis", "Kubernetes"],
    ["Django", "Python", "PostgreSQL", "Docker"],
    ["Ruby on Rails", "Ruby", "MySQL", "Heroku"],
    ["Laravel", "PHP", "MySQL", "DigitalOcean"],
    ["Spring Boot", "Java", "Oracle", "AWS"],
    ["Flask", "Python", "SQLite", "Vercel"],
    ["Express", "Node.js", "MongoDB", "Netlify"]
]

HIRING_SIGNALS = [
    "Product Manager", "Software Engineer", "Data Scientist", 
    "Sales Director", "Marketing Manager", "Customer Success",
    "DevOps Engineer", "UI/UX Designer", "Revenue Operations",
    "Finance Manager", "Business Analyst", "Growth Manager",
    "VP of Sales", "Head of Product", "Engineering Manager"
]

NEWS_TEMPLATES = [
    "{company} raises ${funding}M Series {series} funding",
    "{company} launches new {feature} platform",
    "{company} expands to {market} market",
    "{company} acquires {target} for ${amount}M",
    "{company} announces partnership with {partner}",
    "{company} reports {growth}% revenue growth",
    "{company} opens new office in {location}",
    "{company} hires former {previous_company} executive"
]

JUSTIFICATION_TEMPLATES = [
    "Strong alignment with Recurly's target market showing clear subscription billing needs and revenue optimization opportunities.",
    "Demonstrates excellent fit across multiple dimensions with significant growth indicators and billing complexity.",
    "Shows promising industry fit with emerging subscription business model and scaling challenges.",
    "High-potential lead with strong revenue sophistication and clear need for advanced billing platform.",
    "Good strategic fit with solid platform maturity and growth trajectory indicating billing needs.",
    "Moderate fit showing some alignment with target criteria but may require custom approach.",
    "Emerging opportunity with basic needs that could grow into more sophisticated requirements."
]

NEXT_STEPS_TEMPLATES = [
    "Reach out to {role} team to discuss billing optimization opportunities",
    "Schedule discovery call with product and finance teams",
    "Send targeted case study showcasing similar company success",
    "Connect with revenue operations to understand current challenges",
    "Propose pilot program for subscription billing optimization",
    "Share ROI calculator and implementation timeline",
    "Arrange technical demo focusing on their specific use case"
]

def generate_company_name() -> str:
    """Generate realistic company name"""
    prefix = random.choice(COMPANY_PREFIXES)
    suffix = random.choice(COMPANY_SUFFIXES)
    return f"{prefix}{suffix}"

def generate_domain(company: str) -> str:
    """Generate domain from company name"""
    clean_name = company.lower().replace(" ", "").replace("corp", "").replace("inc", "")
    domains = [".com", ".io", ".co", ".ai", ".tech"]
    return f"{clean_name}{random.choice(domains)}"

def generate_enriched_data(company: str) -> Dict[str, Any]:
    """Generate realistic enriched data for a company"""
    return {
        "company": company,
        "domain": generate_domain(company),
        "industry": random.choice(INDUSTRIES),
        "employee_count": random.randint(10, 5000),
        "funding_stage": random.choice(["Seed", "Series A", "Series B", "Series C", "Growth", "Public"]),
        "tech_stack": random.choice(TECH_STACKS),
        "hiring_signals": random.choices(HIRING_SIGNALS, k=random.randint(1, 5)),
        "news_mentions": [
            NEWS_TEMPLATES[0].format(
                company=company, 
                funding=random.randint(1, 100),
                series=random.choice(["A", "B", "C"])
            ),
            NEWS_TEMPLATES[1].format(
                company=company,
                feature=random.choice(["analytics", "billing", "customer", "payment"])
            )
        ][:random.randint(0, 3)],
        "location": random.choice(["San Francisco", "New York", "Austin", "Seattle", "Boston", "Remote"]),
        "founded_year": random.randint(2010, 2023)
    }

def calculate_score_with_logic(breakdown: Dict[str, int]) -> int:
    """Calculate realistic score based on breakdown with some randomness"""
    base_score = sum(breakdown.values())
    # Add some realistic variance
    variance = random.randint(-5, 5)
    return max(0, min(100, base_score + variance))

def generate_breakdown_scores(industry: str, employee_count: int, funding_stage: str) -> Dict[str, int]:
    """Generate realistic breakdown scores based on company characteristics"""
    
    # Industry fit scoring
    high_fit_industries = ["SaaS", "E-commerce", "Fintech", "Media"]
    industry_fit = random.randint(15, 20) if industry in high_fit_industries else random.randint(8, 15)
    
    # Scale indicators based on employee count
    if employee_count > 1000:
        scale_indicators = random.randint(16, 20)
    elif employee_count > 100:
        scale_indicators = random.randint(12, 18)
    else:
        scale_indicators = random.randint(6, 14)
    
    # Platform maturity based on funding stage
    maturity_map = {"Seed": (6, 12), "Series A": (10, 16), "Series B": (12, 18), 
                   "Series C": (14, 19), "Growth": (16, 20), "Public": (18, 20)}
    min_mat, max_mat = maturity_map.get(funding_stage, (8, 15))
    platform_maturity = random.randint(min_mat, max_mat)
    
    # Growth/churn challenges (higher for faster growing companies)
    growth_churn = random.randint(10, 20)
    
    # Revenue sophistication (correlated with maturity and scale)
    rev_soph_base = (platform_maturity + scale_indicators) // 2
    revenue_sophistication = random.randint(max(6, rev_soph_base - 3), min(20, rev_soph_base + 3))
    
    return {
        "industry_fit": industry_fit,
        "scale_indicators": scale_indicators,
        "platform_maturity": platform_maturity,
        "growth_churn_challenges": growth_churn,
        "revenue_sophistication": revenue_sophistication
    }

def determine_priority(score: int) -> str:
    """Determine priority based on score"""
    if score >= 75:
        return "High"
    elif score >= 50:
        return "Medium"
    else:
        return "Low"

def generate_scored_result(enriched_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate scored result from enriched data"""
    
    breakdown = generate_breakdown_scores(
        enriched_data["industry"],
        enriched_data["employee_count"],
        enriched_data["funding_stage"]
    )
    
    score = calculate_score_with_logic(breakdown)
    priority = determine_priority(score)
    
    # Generate contextual insights based on the data
    insights = []
    if enriched_data["industry"] in ["SaaS", "E-commerce", "Fintech"]:
        insights.append(f"{enriched_data['company']} operates in {enriched_data['industry']}, showing strong fit for subscription billing needs")
    
    if enriched_data["employee_count"] > 200:
        insights.append(f"Company size ({enriched_data['employee_count']} employees) indicates complex billing requirements")
    
    if enriched_data["funding_stage"] in ["Series B", "Series C", "Growth"]:
        insights.append(f"At {enriched_data['funding_stage']} stage, likely facing scaling billing challenges")
    
    result = {
        "company": enriched_data["company"],
        "domain": enriched_data["domain"],
        "score": score,
        "priority": priority,
        "breakdown": breakdown,
        "summary": insights[:3],  # Limit to 3 insights
        "justification": random.choice(JUSTIFICATION_TEMPLATES),
        "next_steps": NEXT_STEPS_TEMPLATES[0].format(role=random.choice(["product", "finance", "revenue ops"]))
    }
    
    return result

def generate_dataset(num_companies: int, output_dir: Path) -> Dict[str, str]:
    """Generate complete dataset with companies, enrichment, and scoring"""
    
    print(f"Generating dataset with {num_companies} companies...")
    
    # Generate company list
    companies = [generate_company_name() for _ in range(num_companies)]
    
    # Create CSV
    csv_path = output_dir / f"sample_companies_{num_companies}.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["company"])
        for company in companies:
            writer.writerow([company])
    
    print(f"✅ Generated {csv_path}")
    
    # Generate enriched data
    enriched_data = [generate_enriched_data(company) for company in companies]
    
    enriched_path = output_dir / f"enriched_sample_{num_companies}.json"
    with open(enriched_path, 'w') as f:
        json.dump(enriched_data, f, indent=2)
    
    print(f"✅ Generated {enriched_path}")
    
    # Generate scored results
    scored_results = [generate_scored_result(data) for data in enriched_data]
    
    scored_path = output_dir / f"scored_sample_{num_companies}.json"
    with open(scored_path, 'w') as f:
        json.dump(scored_results, f, indent=2)
    
    print(f"✅ Generated {scored_path}")
    
    # Generate summary stats
    high_priority = sum(1 for r in scored_results if r['priority'] == 'High')
    medium_priority = sum(1 for r in scored_results if r['priority'] == 'Medium')
    low_priority = sum(1 for r in scored_results if r['priority'] == 'Low')
    avg_score = sum(r['score'] for r in scored_results) / len(scored_results)
    
    summary = {
        "total_companies": num_companies,
        "high_priority": high_priority,
        "medium_priority": medium_priority,
        "low_priority": low_priority,
        "average_score": round(avg_score, 1),
        "generated_at": datetime.now().isoformat()
    }
    
    summary_path = output_dir / f"dataset_summary_{num_companies}.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"✅ Generated summary: {summary}")
    
    return {
        "companies_csv": str(csv_path),
        "enriched_json": str(enriched_path),
        "scored_json": str(scored_path),
        "summary": str(summary_path)
    }

def generate_time_series_data(base_scored_results: List[Dict], days_back: int = 30, output_dir: Path = None):
    """Generate historical data for analytics testing"""
    
    print(f"Generating time series data for {days_back} days...")
    
    if output_dir is None:
        output_dir = Path("data")
    
    # Create analytics directory
    analytics_dir = output_dir.parent / "analytics"
    analytics_dir.mkdir(exist_ok=True)
    
    try:
        import sys
        sys.path.append(str(Path.cwd()))
        from analytics.team_analytics import TeamAnalyticsEngine
    except ImportError as e:
        print(f"⚠️ Could not import TeamAnalyticsEngine: {e}")
        print("   Skipping time series data generation")
        return 0
    
    # Initialize analytics engine
    engine = TeamAnalyticsEngine()
    
    # Generate sessions across time period
    users = ["alice_smith", "bob_jones", "carol_chen", "david_kim", "emma_watson"]
    models = ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"]
    templates = ["recurly_template.txt", "saas_template.txt", "enterprise_template.txt"]
    
    session_count = 0
    
    for day_offset in range(days_back):
        # Generate 1-3 sessions per day
        sessions_today = random.randint(1, 3)
        
        for session_num in range(sessions_today):
            # Create session timestamp
            session_date = datetime.now() - timedelta(days=day_offset)
            session_date = session_date.replace(
                hour=random.randint(9, 17),
                minute=random.randint(0, 59),
                second=random.randint(0, 59)
            )
            
            # Select random subset of results for this session
            session_size = random.randint(5, 20)
            session_results = random.choices(base_scored_results, k=session_size)
            
            # Add some realistic variation to scores for time series
            varied_results = []
            for result in session_results:
                varied_result = result.copy()
                # Add time-based variation
                score_variation = random.randint(-10, 10)
                varied_result['score'] = max(0, min(100, result['score'] + score_variation))
                varied_result['priority'] = determine_priority(varied_result['score'])
                varied_results.append(varied_result)
            
            # Record session
            session_id = engine.record_processing_session(
                results=varied_results,
                user=random.choice(users),
                input_file=f"session_{session_count}_leads.csv",
                processing_time=random.uniform(30.0, 180.0),
                model_used=random.choice(models),
                template_used=random.choice(templates)
            )
            
            session_count += 1
            
            # Update session timestamp in database to match our desired date
            import sqlite3
            conn = sqlite3.connect(engine.db.db_path)
            conn.execute("UPDATE sessions SET timestamp = ? WHERE session_id = ?", 
                        (session_date, session_id))
            conn.execute("UPDATE leads SET timestamp = ? WHERE session_id = ?",
                        (session_date, session_id))
            conn.commit()
            conn.close()
    
    print(f"✅ Generated {session_count} historical sessions")
    return session_count

if __name__ == "__main__":
    # Create output directory
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    
    print("🎲 Recursor Sample Data Generator")
    print("=" * 50)
    
    # Generate different sized datasets
    datasets = []
    
    # Small dataset for quick testing
    print("\n📊 Generating SMALL dataset (50 companies)...")
    small_data = generate_dataset(50, output_dir)
    datasets.append(("Small", small_data))
    
    # Medium dataset for dashboard testing
    print("\n📊 Generating MEDIUM dataset (200 companies)...")
    medium_data = generate_dataset(200, output_dir)
    datasets.append(("Medium", medium_data))
    
    # Large dataset for performance testing
    print("\n📊 Generating LARGE dataset (1000 companies)...")
    large_data = generate_dataset(1000, output_dir)
    datasets.append(("Large", large_data))
    
    # Generate historical data for analytics using medium dataset
    print("\n📈 Generating historical analytics data...")
    with open(medium_data["scored_json"], 'r') as f:
        scored_results = json.load(f)
    
    sessions_created = generate_time_series_data(scored_results, days_back=30, output_dir=output_dir)
    
    # Summary
    print("\n" + "=" * 50)
    print("🎉 DATA GENERATION COMPLETE!")
    print("=" * 50)
    
    for name, data in datasets:
        print(f"\n{name} Dataset:")
        print(f"  📋 Companies CSV: {data['companies_csv']}")
        print(f"  🔍 Enriched JSON: {data['enriched_json']}")
        print(f"  🎯 Scored JSON: {data['scored_json']}")
        print(f"  📊 Summary: {data['summary']}")
    
    print(f"\n📈 Analytics:")
    print(f"  🕐 Historical sessions: {sessions_created}")
    print(f"  📅 Time range: 30 days")
    
    print(f"\n🚀 Ready to test!")
    print(f"  • Use scored JSON files in dashboard 'Upload Results' mode")
    print(f"  • Use CSV files for 'Live Processing' (no API calls needed)")
    print(f"  • Analytics data is ready for 'Team Analytics' mode")
