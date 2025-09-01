#!/usr/bin/env python3
"""
Generate demo data with SaaS/subscription companies that would be actual Recurly prospects
"""

import json
import random
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

def generate_recurly_prospects():
    """Generate realistic SaaS/subscription company prospects"""
    
    prospects = [
        {
            "company": "SubscribeBox",
            "domain": "subscribebox.io",
            "description": "Monthly subscription boxes for niche hobbies and interests",
            "industry": "E-commerce Subscription",
            "employee_range": "50-200",
            "revenue_signals": ["monthly recurring revenue", "subscription billing", "churn reduction"],
            "tech_stack": ["Shopify", "React", "PostgreSQL", "Stripe"],
            "hiring_signals": ["Senior Full Stack Engineer", "Head of Growth", "Customer Success Manager"],
            "growth_indicators": ["Series A funding", "40% YoY growth", "expanding to EU market"],
            "pain_points": ["payment processing complexity", "subscription lifecycle management", "revenue recognition"]
        },
        {
            "company": "LearningPath",
            "domain": "learningpath.com",
            "description": "Online course platform with subscription-based access",
            "industry": "EdTech SaaS",
            "employee_range": "100-500", 
            "revenue_signals": ["SaaS metrics", "monthly active users", "course completion rates"],
            "tech_stack": ["Vue.js", "Node.js", "MongoDB", "AWS"],
            "hiring_signals": ["Product Manager", "DevOps Engineer", "Sales Development Representative"],
            "growth_indicators": ["bootstrapped profitability", "enterprise clients", "mobile app launch"],
            "pain_points": ["billing complexity", "international payments", "subscription analytics"]
        },
        {
            "company": "FitnessFlow",
            "domain": "fitnessflow.app",
            "description": "Fitness app with premium subscription tiers and personal training",
            "industry": "Health & Wellness SaaS",
            "employee_range": "25-100",
            "revenue_signals": ["freemium model", "premium subscriptions", "in-app purchases"],
            "tech_stack": ["React Native", "Firebase", "Stripe", "iOS/Android"],
            "hiring_signals": ["iOS Developer", "Backend Engineer", "Marketing Manager"],
            "growth_indicators": ["1M+ downloads", "venture funding", "corporate partnerships"],
            "pain_points": ["subscription churn", "payment failures", "pricing optimization"]
        },
        {
            "company": "DataDash",
            "domain": "datadash.co",
            "description": "Business intelligence platform with usage-based pricing",
            "industry": "Data & Analytics SaaS",
            "employee_range": "200-1000",
            "revenue_signals": ["usage-based billing", "enterprise contracts", "seat-based pricing"],
            "tech_stack": ["Python", "React", "PostgreSQL", "Kubernetes"],
            "hiring_signals": ["Senior Data Engineer", "Enterprise Account Executive", "Customer Success"],
            "growth_indicators": ["Series B funding", "Fortune 500 clients", "international expansion"],
            "pain_points": ["complex billing scenarios", "revenue reporting", "dunning management"]
        },
        {
            "company": "CloudSync",
            "domain": "cloudsync.io",
            "description": "File sync and collaboration tool for distributed teams",
            "industry": "Productivity SaaS",
            "employee_range": "150-500",
            "revenue_signals": ["per-seat pricing", "storage-based billing", "team plans"],
            "tech_stack": ["Go", "React", "PostgreSQL", "AWS S3"],
            "hiring_signals": ["Platform Engineer", "Sales Engineer", "VP of Sales"],
            "growth_indicators": ["remote work adoption", "enterprise migration", "API partnerships"],
            "pain_points": ["subscription management", "billing integration", "payment processing"]
        },
        {
            "company": "StreamlineHR",
            "domain": "streamlinehr.com",
            "description": "HR management platform with per-employee pricing",
            "industry": "HR Tech SaaS",
            "employee_range": "75-300",
            "revenue_signals": ["per-employee billing", "annual contracts", "add-on modules"],
            "tech_stack": ["Angular", "Java", "MySQL", "Azure"],
            "hiring_signals": ["Full Stack Developer", "Implementation Specialist", "Account Manager"],
            "growth_indicators": ["mid-market focus", "compliance features", "integration partnerships"],
            "pain_points": ["complex pricing tiers", "proration calculations", "multi-entity billing"]
        },
        {
            "company": "RetailRocket",
            "domain": "retailrocket.com",
            "description": "E-commerce personalization engine with transaction-based fees",
            "industry": "E-commerce Technology",
            "employee_range": "100-400",
            "revenue_signals": ["transaction-based pricing", "revenue sharing", "performance fees"],
            "tech_stack": ["Python", "React", "Redis", "Elasticsearch"],
            "hiring_signals": ["Machine Learning Engineer", "Solutions Engineer", "Head of Partnerships"],
            "growth_indicators": ["Shopify app store", "enterprise retailers", "AI/ML capabilities"],
            "pain_points": ["variable billing models", "revenue attribution", "partner payouts"]
        },
        {
            "company": "SecureVault",
            "domain": "securevault.io",
            "description": "Password manager with team and enterprise plans",
            "industry": "Cybersecurity SaaS",
            "employee_range": "50-200",
            "revenue_signals": ["freemium conversion", "enterprise security", "compliance features"],
            "tech_stack": ["React", "Node.js", "MongoDB", "end-to-end encryption"],
            "hiring_signals": ["Security Engineer", "Enterprise Sales", "Product Marketing Manager"],
            "growth_indicators": ["security compliance", "enterprise adoption", "mobile security"],
            "pain_points": ["subscription lifecycle", "enterprise billing", "security compliance"]
        },
        {
            "company": "ContentCrafter",
            "domain": "contentcrafter.ai",
            "description": "AI-powered content generation with usage-based pricing",
            "industry": "AI/ML SaaS",
            "employee_range": "25-100",
            "revenue_signals": ["API usage billing", "credit-based system", "enterprise licenses"],
            "tech_stack": ["Python", "React", "PostgreSQL", "OpenAI API"],
            "hiring_signals": ["AI Engineer", "Growth Marketing", "Developer Relations"],
            "growth_indicators": ["AI content demand", "API partnerships", "enterprise adoption"],
            "pain_points": ["usage tracking", "overage billing", "API monetization"]
        },
        {
            "company": "TeamTracker",
            "domain": "teamtracker.app",
            "description": "Project management tool with flexible team pricing",
            "industry": "Project Management SaaS", 
            "employee_range": "40-150",
            "revenue_signals": ["per-user pricing", "project-based billing", "time tracking"],
            "tech_stack": ["Vue.js", "Laravel", "MySQL", "WebSocket"],
            "hiring_signals": ["Frontend Developer", "Customer Success", "Sales Manager"],
            "growth_indicators": ["remote team adoption", "integration ecosystem", "mobile apps"],
            "pain_points": ["flexible billing", "team management", "usage analytics"]
        }
    ]
    
    return prospects

def generate_scored_results():
    """Generate realistic scoring results for these prospects"""
    prospects = generate_recurly_prospects()
    scored_results = []
    
    for prospect in prospects:
        # Generate realistic scores based on company profile
        base_score = random.randint(60, 95)
        
        # Adjust score based on company characteristics
        if "Series" in str(prospect.get("growth_indicators", [])):
            base_score += random.randint(5, 15)  # Funded companies score higher
        
        if "enterprise" in str(prospect.get("revenue_signals", [])).lower():
            base_score += random.randint(3, 10)  # Enterprise focus is good
            
        if any("billing" in pain.lower() or "payment" in pain.lower() 
               for pain in prospect.get("pain_points", [])):
            base_score += random.randint(5, 20)  # Direct pain point match
        
        # Cap at 100
        final_score = min(base_score, 100)
        
        # Determine priority based on score
        if final_score >= 85:
            priority = "High"
        elif final_score >= 70:
            priority = "Medium"
        else:
            priority = "Low"
        
        # Generate breakdown scores that add up appropriately
        breakdown = {
            "industry_fit": random.randint(15, 20),
            "scale_indicators": random.randint(12, 18), 
            "platform_maturity": random.randint(14, 19),
            "growth_churn_challenges": random.randint(13, 19),
            "revenue_sophistication": random.randint(12, 18)
        }
        
        # Generate justification based on company data
        pain_points = prospect.get("pain_points", [])
        justification_parts = []
        
        if any("billing" in pain or "payment" in pain for pain in pain_points):
            justification_parts.append("Strong fit: company has direct billing/payment complexity challenges")
        
        if "subscription" in prospect["description"].lower():
            justification_parts.append("Perfect target: subscription-based business model")
            
        if prospect.get("employee_range", "").split("-")[0].isdigit():
            employee_count = int(prospect["employee_range"].split("-")[0])
            if employee_count >= 50:
                justification_parts.append("Good scale: sufficient team size for enterprise subscription management")
        
        if any("enterprise" in str(indicator).lower() for indicator in prospect.get("growth_indicators", [])):
            justification_parts.append("Enterprise ready: showing signs of enterprise market adoption")
            
        justification = ". ".join(justification_parts) + "."
        
        # Generate summary points
        summary_points = []
        
        if prospect.get("revenue_signals"):
            summary_points.append(f"Revenue model: {', '.join(prospect['revenue_signals'][:2])}")
            
        if prospect.get("growth_indicators"):
            summary_points.append(f"Growth stage: {prospect['growth_indicators'][0]}")
            
        if prospect.get("tech_stack"):
            summary_points.append(f"Tech stack includes: {', '.join(prospect['tech_stack'][:3])}")
            
        # Generate next steps
        next_steps_options = [
            "Schedule discovery call to discuss current billing pain points",
            "Send Recurly ROI calculator and subscription billing guide", 
            "Connect with technical team to discuss integration requirements",
            "Arrange demo focusing on subscription lifecycle management",
            "Share case studies from similar subscription businesses"
        ]
        
        next_steps = random.choice(next_steps_options)
        
        scored_result = {
            "company": prospect["company"],
            "domain": prospect["domain"], 
            "score": final_score,
            "priority": priority,
            "breakdown": breakdown,
            "justification": justification,
            "summary": summary_points,
            "next_steps": next_steps,
            "industry": prospect["industry"],
            "employee_range": prospect["employee_range"],
            "description": prospect["description"]
        }
        
        scored_results.append(scored_result)
    
    # Sort by score descending
    scored_results.sort(key=lambda x: x["score"], reverse=True)
    
    return scored_results

def save_demo_data():
    """Save demo data to files for easy loading"""
    scored_results = generate_scored_results()
    
    # Create data directory if it doesn't exist
    data_dir = Path("data/demo")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Save scored results
    with open(data_dir / "recurly_prospects_scored.json", "w") as f:
        json.dump(scored_results, f, indent=2)
    
    print(f"✅ Generated {len(scored_results)} Recurly prospect leads")
    print("📁 Saved to: data/demo/recurly_prospects_scored.json")
    
    # Print summary
    high_priority = len([r for r in scored_results if r["priority"] == "High"])
    medium_priority = len([r for r in scored_results if r["priority"] == "Medium"]) 
    low_priority = len([r for r in scored_results if r["priority"] == "Low"])
    
    print(f"\n📊 Lead Breakdown:")
    print(f"  🔴 High Priority: {high_priority}")
    print(f"  🟡 Medium Priority: {medium_priority}")
    print(f"  ⚪ Low Priority: {low_priority}")
    
    avg_score = sum(r["score"] for r in scored_results) / len(scored_results)
    print(f"  📈 Average Score: {avg_score:.1f}")
    
    return scored_results

if __name__ == "__main__":
    print("🎯 Generating Recurly-focused demo data...")
    results = save_demo_data()
    print("\n🚀 Demo data ready! Use this file for realistic lead scoring demos.")
