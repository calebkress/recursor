#!/usr/bin/env python3
"""
Create a fresh sales team database with realistic users and known passwords
"""

import os
import sys
import sqlite3
from pathlib import Path

# Add parent directory to path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from auth.user_manager import UserManager, UserRole, TeamRole

def purge_database():
    """Remove existing database to start fresh"""
    db_path = Path("auth/users.db")
    if db_path.exists():
        os.remove(db_path)
        print("🗑️  Purged existing database")

def create_sales_team():
    """Create a realistic 15-person sales team with known passwords"""
    
    # Initialize user manager (will create fresh DB)
    um = UserManager()
    print("📊 Created fresh database")
    
    # All users will use the same simple password for demo purposes
    password = "password123"
    
    users = []
    
    # 1. Admin account (you)
    admin_id = um.create_user(
        email="caleb@recursor.com",
        username="caleb",
        password=password,
        first_name="Caleb",
        last_name="Kress",
        role=UserRole.MANAGER
    )
    users.append(("Admin", "caleb@recursor.com", "Caleb Kress", "Manager"))
    
    # 2-3. Sales Managers (2 people)
    manager_data = [
        ("sarah@recursor.com", "sarah", "Sarah", "Chen", "West Coast Sales Manager"),
        ("mike@recursor.com", "mike", "Mike", "Rodriguez", "East Coast Sales Manager")
    ]
    
    for email, username, first, last, title in manager_data:
        user_id = um.create_user(
            email=email,
            username=username, 
            password=password,
            first_name=first,
            last_name=last,
            role=UserRole.MANAGER
        )
        users.append(("Manager", email, f"{first} {last}", "Manager"))
    
    # 4-10. Account Executives (7 people)
    ae_data = [
        ("alex@recursor.com", "alex", "Alex", "Thompson", "Senior AE"),
        ("jessica@recursor.com", "jessica", "Jessica", "Williams", "Enterprise AE"),
        ("david@recursor.com", "david", "David", "Brown", "Mid-Market AE"),
        ("lisa@recursor.com", "lisa", "Lisa", "Davis", "Commercial AE"),
        ("ryan@recursor.com", "ryan", "Ryan", "Wilson", "Senior AE"),
        ("maria@recursor.com", "maria", "Maria", "Garcia", "Enterprise AE"),
        ("james@recursor.com", "james", "James", "Martinez", "Commercial AE")
    ]
    
    for email, username, first, last, title in ae_data:
        user_id = um.create_user(
            email=email,
            username=username,
            password=password,
            first_name=first,
            last_name=last,
            role=UserRole.ACCOUNT_EXECUTIVE
        )
        users.append(("Account Executive", email, f"{first} {last}", "Account Executive"))
    
    # 11-16. Sales Development Representatives (6 people)  
    sdr_data = [
        ("emma@recursor.com", "emma", "Emma", "Johnson", "SDR - Outbound"),
        ("noah@recursor.com", "noah", "Noah", "Miller", "SDR - Inbound"),
        ("sophia@recursor.com", "sophia", "Sophia", "Anderson", "Senior SDR"),
        ("liam@recursor.com", "liam", "Liam", "Taylor", "SDR - Enterprise"),
        ("olivia@recursor.com", "olivia", "Olivia", "Thomas", "SDR - Mid-Market"), 
        ("ethan@recursor.com", "ethan", "ethan", "White", "Junior SDR")
    ]
    
    for email, username, first, last, title in sdr_data:
        user_id = um.create_user(
            email=email,
            username=username,
            password=password,
            first_name=first,
            last_name=last,
            role=UserRole.SALES_DEVELOPMENT_REPRESENTATIVE
        )
        users.append(("SDR", email, f"{first} {last}", "Sales Development Representative"))
    
    print(f"👥 Created {len(users)} team members")
    
    # Create teams
    teams = []
    
    # West Coast Team (Sarah as owner)
    sarah_id = um.get_user_by_email("sarah@recursor.com")
    west_team_id = um.create_team(
        name="West Coast Sales",
        description="West Coast sales team covering California, Oregon, Washington",
        owner_id=sarah_id.user_id if sarah_id else admin_id
    )
    teams.append(("West Coast Sales", "sarah@recursor.com"))
    
    # East Coast Team (Mike as owner)  
    mike_id = um.get_user_by_email("mike@recursor.com")
    east_team_id = um.create_team(
        name="East Coast Sales",
        description="East Coast sales team covering NY, MA, PA, FL",
        owner_id=mike_id.user_id if mike_id else admin_id
    )
    teams.append(("East Coast Sales", "mike@recursor.com"))
    
    # Enterprise Team (mixed coast, Jessica as owner)
    jessica_id = um.get_user_by_email("jessica@recursor.com") 
    enterprise_team_id = um.create_team(
        name="Enterprise Sales",
        description="Enterprise accounts team handling Fortune 500 clients",
        owner_id=jessica_id.user_id if jessica_id else admin_id
    )
    teams.append(("Enterprise Sales", "jessica@recursor.com"))
    
    print(f"🏢 Created {len(teams)} teams")
    
    return users, teams, password

def get_user_by_email(um, email):
    """Helper to get user by email"""
    conn = sqlite3.connect(um.db_path)
    cursor = conn.execute("SELECT user_id FROM users WHERE email = ?", (email,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return um.get_user(result[0])
    return None

# Monkey patch the method for this script
UserManager.get_user_by_email = lambda self, email: get_user_by_email(self, email)

def print_team_summary(users, teams, password):
    """Print a nice summary of the created team"""
    
    print("\n" + "="*60)
    print("🎯 RECURSOR SALES TEAM CREATED!")
    print("="*60)
    
    print(f"\n🔑 Universal Password: {password}")
    print("   (All accounts use the same password for demo purposes)")
    
    print("\n👥 TEAM ROSTER:")
    print("-" * 60)
    
    # Group by role
    by_role = {}
    for role, email, name, role_display in users:
        if role not in by_role:
            by_role[role] = []
        by_role[role].append((email, name))
    
    for role in ["Admin", "Manager", "Account Executive", "SDR"]:
        if role in by_role:
            print(f"\n{role.upper()}S:")
            for email, name in by_role[role]:
                print(f"  • {name:<20} | {email}")
    
    print(f"\n🏢 TEAMS:")
    print("-" * 60)
    for team_name, owner_email in teams:
        print(f"  • {team_name:<20} | Owner: {owner_email}")
    
    print(f"\n📊 SUMMARY:")
    print("-" * 60)
    print(f"  Total Users: {len(users)}")
    print(f"  Total Teams: {len(teams)}")
    print(f"  Managers: {len(by_role.get('Manager', []))} + 1 Admin")
    print(f"  Account Executives: {len(by_role.get('Account Executive', []))}")
    print(f"  Sales Development Reps: {len(by_role.get('SDR', []))}")
    
    print(f"\n🚀 Ready to use! Login with any email and password: {password}")
    print("="*60)

if __name__ == "__main__":
    print("🔄 Setting up fresh Recursor sales team database...")
    
    # Change to project root directory
    os.chdir(Path(__file__).parent.parent)
    
    purge_database()
    users, teams, password = create_sales_team()
    print_team_summary(users, teams, password)
    
    print("\n✅ Database setup complete! Run 'streamlit run dashboard.py' to get started.")
