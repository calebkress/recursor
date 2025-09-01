#!/usr/bin/env python3
"""
Multi-User Demo Setup Script for Recursor
Creates demo users, teams, and sample data for testing multi-user features
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from auth.user_manager import UserManager, UserRole, TeamRole
from analytics.multi_tenant_analytics import MultiTenantAnalyticsEngine
import json

def setup_demo_users():
    """Create demo users with different roles"""
    user_manager = UserManager()
    
    # Demo users to create
    demo_users = [
        {
            "email": "alice@example.com",
            "username": "alice",
            "password": "Password123",
            "first_name": "Alice",
            "last_name": "Johnson",
            "role": UserRole.TEAM_LEAD
        },
        {
            "email": "bob@example.com", 
            "username": "bob",
            "password": "Password123",
            "first_name": "Bob",
            "last_name": "Smith",
            "role": UserRole.ANALYST
        },
        {
            "email": "carol@example.com",
            "username": "carol", 
            "password": "Password123",
            "first_name": "Carol",
            "last_name": "Davis",
            "role": UserRole.ANALYST
        },
        {
            "email": "david@example.com",
            "username": "david",
            "password": "Password123", 
            "first_name": "David",
            "last_name": "Wilson",
            "role": UserRole.VIEWER
        }
    ]
    
    created_users = {}
    
    for user_data in demo_users:
        try:
            user_id = user_manager.create_user(**user_data)
            created_users[user_data["username"]] = user_id
            print(f"✅ Created user: {user_data['first_name']} {user_data['last_name']} ({user_data['email']})")
        except ValueError as e:
            print(f"⚠️ User {user_data['email']} might already exist: {e}")
            # Try to find existing user
            try:
                token = user_manager.authenticate_user(user_data["email"], user_data["password"])
                if token:
                    user_id = user_manager.verify_token(token)
                    created_users[user_data["username"]] = user_id
                    print(f"🔍 Found existing user: {user_data['email']}")
            except Exception:
                pass
    
    return created_users

def setup_demo_teams(created_users):
    """Create demo teams and assign users"""
    user_manager = UserManager()
    
    teams_to_create = [
        {
            "name": "Sales Analytics Team",
            "description": "Team focused on lead scoring and sales intelligence",
            "owner": "alice",
            "members": {
                "bob": TeamRole.MEMBER,
                "carol": TeamRole.ADMIN,
                "david": TeamRole.GUEST
            }
        },
        {
            "name": "Marketing Intelligence",
            "description": "Marketing team using Recursor for lead generation",
            "owner": "bob", 
            "members": {
                "carol": TeamRole.MEMBER
            }
        }
    ]
    
    created_teams = {}
    
    for team_data in teams_to_create:
        if team_data["owner"] not in created_users:
            print(f"❌ Cannot create team {team_data['name']}: owner not found")
            continue
        
        try:
            team_id = user_manager.create_team(
                name=team_data["name"],
                description=team_data["description"],
                owner_id=created_users[team_data["owner"]]
            )
            
            created_teams[team_data["name"]] = team_id
            print(f"✅ Created team: {team_data['name']}")
            
            # Add members
            for member_username, role in team_data["members"].items():
                if member_username in created_users:
                    # Get user email for invitation
                    user = user_manager.get_user(created_users[member_username])
                    if user:
                        success = user_manager.invite_user_to_team(
                            team_id=team_id,
                            user_email=user.email,
                            role=role,
                            invited_by=created_users[team_data["owner"]]
                        )
                        if success:
                            print(f"  ➕ Added {user.first_name} {user.last_name} as {role.value}")
                        else:
                            print(f"  ❌ Failed to add {user.email}")
                            
        except Exception as e:
            print(f"❌ Failed to create team {team_data['name']}: {e}")
    
    return created_teams

def setup_demo_analytics_data(created_users, created_teams):
    """Create demo analytics data for teams"""
    analytics_engine = MultiTenantAnalyticsEngine()
    
    # Demo results data
    demo_results = [
        {
            "company": "TechCorp",
            "domain": "techcorp.com",
            "score": 85,
            "priority": "High", 
            "breakdown": {
                "industry_fit": 18,
                "scale_indicators": 17,
                "platform_maturity": 16,
                "growth_churn_challenges": 17,
                "revenue_sophistication": 17
            }
        },
        {
            "company": "StartupInc",
            "domain": "startup.io",
            "score": 72,
            "priority": "Medium",
            "breakdown": {
                "industry_fit": 15,
                "scale_indicators": 14,
                "platform_maturity": 15,
                "growth_churn_challenges": 14,
                "revenue_sophistication": 14
            }
        },
        {
            "company": "BigCorp",
            "domain": "bigcorp.com", 
            "score": 91,
            "priority": "High",
            "breakdown": {
                "industry_fit": 19,
                "scale_indicators": 18,
                "platform_maturity": 18,
                "growth_churn_challenges": 18,
                "revenue_sophistication": 18
            }
        }
    ]
    
    # Create sessions for different teams and users
    sessions_created = 0
    
    for team_name, team_id in created_teams.items():
        for user_key, user_id in created_users.items():
            # Check if user is in this team
            if analytics_engine.user_manager.check_team_permission(user_id, team_id):
                user = analytics_engine.user_manager.get_user(user_id)
                if user:
                    session_id = analytics_engine.record_processing_session(
                        results=demo_results,
                        user=user.username,
                        team_id=team_id,
                        input_file=f"{team_name.lower().replace(' ', '_')}_leads.csv",
                        processing_time=45.0,
                        model_used="gpt-4-turbo",
                        template_used="recurly_template.txt"
                    )
                    sessions_created += 1
                    print(f"📊 Created analytics session for {user.first_name} in {team_name}")
    
    print(f"✅ Created {sessions_created} demo analytics sessions")

def main():
    print("🚀 Setting up Multi-User Demo for Recursor")
    print("=" * 50)
    
    # Create demo users
    print("\n👥 Creating Demo Users...")
    created_users = setup_demo_users()
    
    # Create demo teams
    print(f"\n🏢 Creating Demo Teams...")
    created_teams = setup_demo_teams(created_users)
    
    # Create demo analytics data
    print(f"\n📊 Creating Demo Analytics Data...")
    setup_demo_analytics_data(created_users, created_teams)
    
    print("\n" + "=" * 50)
    print("🎉 MULTI-USER DEMO SETUP COMPLETE!")
    print("=" * 50)
    
    print("\n📋 Demo Accounts Created:")
    print("  Email: alice@example.com | Password: Password123 | Role: Team Lead")
    print("  Email: bob@example.com   | Password: Password123 | Role: Analyst") 
    print("  Email: carol@example.com | Password: Password123 | Role: Analyst")
    print("  Email: david@example.com | Password: Password123 | Role: Viewer")
    
    print(f"\n🏢 Demo Teams:")
    for team_name in created_teams.keys():
        print(f"  • {team_name}")
    
    print(f"\n🎯 Ready to test!")
    print(f"  • Launch dashboard: streamlit run dashboard.py")
    print(f"  • Login with any of the demo accounts above")
    print(f"  • Explore team features, analytics, and collaboration")

if __name__ == "__main__":
    main()
