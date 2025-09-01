#!/usr/bin/env python3
"""
Analytics Demo Data Generator for Recursor
Creates realistic analytics data for the Team Analytics dashboard feature
"""

import json
import random
import sqlite3
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Sample data for demo
USERS = ["alice_smith", "bob_jones", "carol_chen", "david_kim", "emma_watson"]
MODELS = ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"]
TEMPLATES = ["recurly_template.txt", "saas_template.txt", "enterprise_template.txt"]

COMPANY_NAMES = [
    "Acme Corp", "Beta Software", "CloudTech", "DataSystems", "Echo AI",
    "Fusion Labs", "GlobalSoft", "HyperCloud", "Infinite Tech", "JetStream",
    "KeyLogic", "Lightning AI", "MetaWorks", "NexusHub", "OmniSoft",
    "PrimeData", "QuantumTech", "RapidSoft", "SmartSystems", "TurboCloud"
]

def create_demo_database(days_back=30):
    """Create a demo database with historical analytics data"""
    print(f"Generating analytics demo data for {days_back} days...")
    
    # Create analytics directory
    analytics_dir = Path("analytics")
    analytics_dir.mkdir(exist_ok=True)
    
    # Set up database file
    db_path = analytics_dir / "team_analytics.db"
    if db_path.exists():
        print(f"Removing existing database at {db_path}")
        os.remove(db_path)
    
    # Create tables
    conn = sqlite3.connect(db_path)
    
    # Sessions table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            input_file TEXT NOT NULL,
            total_leads INTEGER NOT NULL,
            processed_leads INTEGER NOT NULL,
            success_rate REAL NOT NULL,
            avg_score REAL NOT NULL,
            high_priority_count INTEGER NOT NULL,
            processing_time REAL NOT NULL,
            model_used TEXT NOT NULL,
            template_used TEXT NOT NULL,
            clustering_enabled BOOLEAN NOT NULL,
            clusters_created INTEGER NOT NULL
        )
    """)
    
    # Leads table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            domain TEXT,
            score INTEGER NOT NULL,
            priority TEXT NOT NULL,
            industry_fit REAL NOT NULL,
            scale_indicators REAL NOT NULL,
            platform_maturity REAL NOT NULL,
            growth_churn_challenges REAL NOT NULL,
            revenue_sophistication REAL NOT NULL,
            processing_time REAL NOT NULL,
            session_id TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            cluster_id TEXT,
            cluster_label TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions (session_id)
        )
    """)
    
    # Generate sessions across time period
    session_count = 0
    total_leads = 0
    
    # Create time variation to simulate real usage pattern
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
            
            # Generate session data
            session_id = f"session_{datetime.now().strftime('%Y%m%d')}_{session_count}"
            user = random.choice(USERS)
            model = random.choice(MODELS)
            template = random.choice(TEMPLATES)
            
            # Session metrics
            session_size = random.randint(5, 15)
            processing_time = random.uniform(30.0, 180.0)
            success_rate = random.uniform(0.85, 1.0)
            processed_leads = int(session_size * success_rate)
            
            # Score distribution - skew based on day to create trends
            base_score = 65 + (day_offset % 7) * 2
            avg_score = min(85, max(55, base_score + random.randint(-10, 10)))
            
            # Generate leads for this session
            leads = []
            high_priority_count = 0
            
            for i in range(session_size):
                company = random.choice(COMPANY_NAMES)
                domain = f"{company.lower().replace(' ', '')}.com"
                
                # Generate score with some variance
                score = min(100, max(30, avg_score + random.randint(-15, 15)))
                
                # Determine priority
                if score >= 75:
                    priority = "High"
                    high_priority_count += 1
                elif score >= 50:
                    priority = "Medium"
                else:
                    priority = "Low"
                
                # Generate breakdown scores
                industry_fit = random.randint(10, 20)
                scale_indicators = random.randint(10, 20)
                platform_maturity = random.randint(10, 20)
                growth_churn_challenges = random.randint(10, 20)
                revenue_sophistication = random.randint(10, 20)
                
                leads.append({
                    "company": company,
                    "domain": domain,
                    "score": score,
                    "priority": priority,
                    "industry_fit": industry_fit,
                    "scale_indicators": scale_indicators,
                    "platform_maturity": platform_maturity,
                    "growth_churn_challenges": growth_churn_challenges,
                    "revenue_sophistication": revenue_sophistication,
                    "processing_time": processing_time / session_size,
                    "session_id": session_id,
                    "timestamp": session_date.isoformat()
                })
            
            # Insert session into database
            conn.execute("""
                INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, user, session_date.isoformat(), f"batch_{session_count}.csv",
                session_size, processed_leads, success_rate, avg_score, high_priority_count,
                processing_time, model, template, False, 0
            ))
            
            # Insert leads into database
            for lead in leads:
                conn.execute("""
                    INSERT INTO leads (
                        company, domain, score, priority, industry_fit, scale_indicators,
                        platform_maturity, growth_churn_challenges, revenue_sophistication,
                        processing_time, session_id, timestamp, cluster_id, cluster_label
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    lead["company"], lead["domain"], lead["score"], lead["priority"],
                    lead["industry_fit"], lead["scale_indicators"], lead["platform_maturity"],
                    lead["growth_churn_challenges"], lead["revenue_sophistication"],
                    lead["processing_time"], lead["session_id"], lead["timestamp"],
                    None, None  # No clustering data for demo
                ))
            
            session_count += 1
            total_leads += session_size
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print(f"✅ Generated analytics demo database at {db_path}")
    print(f"  - Total sessions: {session_count}")
    print(f"  - Total leads processed: {total_leads}")
    
    return db_path, session_count, total_leads

if __name__ == "__main__":
    print("📊 Recursor Analytics Demo Generator")
    print("=" * 50)
    
    db_path, sessions, leads = create_demo_database(days_back=30)
    
    print("\n" + "=" * 50)
    print("🎉 ANALYTICS DEMO DATA GENERATION COMPLETE!")
    print("=" * 50)
    print(f"\nDatabase: {db_path}")
    print(f"Sessions: {sessions}")
    print(f"Leads: {leads}")
    print(f"Time range: 30 days")
    
    print("\n🚀 Ready to test!")
    print("  • Launch the dashboard and select 'Team Analytics' mode")
    print("  • Data will be automatically loaded from the demo database")
