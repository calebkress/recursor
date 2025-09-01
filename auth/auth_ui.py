#!/usr/bin/env python3
"""
Authentication UI Components for Recursor Dashboard
Streamlit-based login, registration, and user management interface
"""

import streamlit as st
import re
from typing import Optional, Dict, Any
from auth.user_manager import UserManager, User, UserRole, TeamRole

def init_auth_state():
    """Initialize authentication session state"""
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'auth_token' not in st.session_state:
        st.session_state.auth_token = None
    if 'user_manager' not in st.session_state:
        st.session_state.user_manager = UserManager()

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    return True, "Password is strong"

def show_login_form():
    """Display login form"""
    st.title("🔐 Login to Recursor")
    
    # Debug login option
    with st.expander("🔧 Debug Login", expanded=False):
        if st.button("Login as Test User"):
            try:
                user_manager = st.session_state.user_manager
                token = user_manager.authenticate_user('test@example.com', 'password123')
                
                if token:
                    user_id = user_manager.verify_token(token)
                    user = user_manager.get_user(user_id)
                    
                    if user:
                        st.session_state.user = user
                        st.session_state.auth_token = token
                        st.success(f"Debug login successful: {user.first_name} {user.last_name}")
                        st.rerun()
                    else:
                        st.error("Failed to get user data")
                else:
                    st.error("Debug login failed")
            except Exception as e:
                st.error(f"Debug login error: {e}")
    
    with st.form("login_form"):
        email = st.text_input("Email Address", placeholder="your@email.com")
        password = st.text_input("Password", type="password")
        
        col1, col2 = st.columns(2)
        
        with col1:
            login_submitted = st.form_submit_button("🚀 Login", use_container_width=True)
        
        with col2:
            if st.form_submit_button("📝 Create Account", use_container_width=True):
                st.session_state.show_registration = True
                st.rerun()
    
    if login_submitted:
        if not email or not password:
            st.error("Please enter both email and password")
            return
        
        try:
            user_manager = st.session_state.user_manager
            token = user_manager.authenticate_user(email, password)
            
            if token:
                # Get user data
                user_id = user_manager.verify_token(token)
                user = user_manager.get_user(user_id)
                
                if user:
                    st.session_state.user = user
                    st.session_state.auth_token = token
                    st.success(f"Welcome back, {user.first_name}!")
                    st.rerun()
                else:
                    st.error("Failed to load user data")
            else:
                st.error("Invalid email or password")
                
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Login failed: {e}")

def show_registration_form():
    """Display registration form"""
    st.title("📝 Create Your Account")
    
    with st.form("registration_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            first_name = st.text_input("First Name", placeholder="John")
            email = st.text_input("Email Address", placeholder="john@company.com")
            password = st.text_input("Password", type="password")
        
        with col2:
            last_name = st.text_input("Last Name", placeholder="Doe")
            username = st.text_input("Username", placeholder="johndoe")
            confirm_password = st.text_input("Confirm Password", type="password")
        
        role = st.selectbox(
            "Role",
            ["Analyst", "Team Lead", "Viewer"],
            help="Your role determines your permissions in the system"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            register_submitted = st.form_submit_button("🎯 Create Account", use_container_width=True)
        
        with col2:
            if st.form_submit_button("← Back to Login", use_container_width=True):
                st.session_state.show_registration = False
                st.rerun()
    
    if register_submitted:
        # Validation
        errors = []
        
        if not all([first_name, last_name, email, username, password, confirm_password]):
            errors.append("All fields are required")
        
        if not validate_email(email):
            errors.append("Please enter a valid email address")
        
        if password != confirm_password:
            errors.append("Passwords do not match")
        
        is_strong, password_msg = validate_password(password)
        if not is_strong:
            errors.append(password_msg)
        
        if len(username) < 3:
            errors.append("Username must be at least 3 characters long")
        
        if errors:
            for error in errors:
                st.error(error)
            return
        
        # Map role
        role_mapping = {
            "Analyst": UserRole.ANALYST,
            "Team Lead": UserRole.TEAM_LEAD,
            "Viewer": UserRole.VIEWER
        }
        user_role = role_mapping[role]
        
        try:
            user_manager = st.session_state.user_manager
            user_id = user_manager.create_user(
                email=email,
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=user_role
            )
            
            st.success("🎉 Account created successfully!")
            st.info("You can now log in with your credentials")
            
            # Switch back to login
            st.session_state.show_registration = False
            st.rerun()
            
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Registration failed: {e}")

def show_user_profile():
    """Display user profile and settings"""
    user = st.session_state.user
    
    # Back to dashboard button
    if st.button("← Back to Dashboard", key="back_to_dashboard"):
        st.session_state.show_profile = False
        st.rerun()
    
    st.title(f"👋 Welcome, {user.first_name}!")
    
    # User info card
    with st.container():
        st.markdown("### 👤 Profile Information")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Name", f"{user.first_name} {user.last_name}")
            st.metric("Email", user.email)
        
        with col2:
            st.metric("Username", user.username)
            st.metric("Role", user.role.value.title())
        
        with col3:
            st.metric("Status", "Active" if user.is_active else "Inactive")
            st.metric("Member Since", user.created_at.strftime("%B %Y"))
    
    # Teams section
    st.markdown("### 🏢 Your Teams")
    
    user_manager = st.session_state.user_manager
    teams = user_manager.get_user_teams(user.user_id)
    
    if teams:
        for team in teams:
            with st.expander(f"🏢 {team['name']} ({team['user_role'].title()})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Description:** {team['description'] or 'No description'}")
                    st.write(f"**Your Role:** {team['user_role'].title()}")
                
                with col2:
                    st.write(f"**Joined:** {team['joined_at'][:10]}")
                    
                    # Show team members if user has permission
                    if team['user_role'] in ['owner', 'admin']:
                        members = user_manager.get_team_members(team['team_id'])
                        st.write(f"**Members:** {len(members)}")
                        
                        if st.button(f"Manage {team['name']}", key=f"manage_{team['team_id']}"):
                            st.session_state.selected_team = team['team_id']
                            st.session_state.show_team_management = True
                            st.rerun()
    else:
        st.info("You're not part of any teams yet. Create a team or ask to be invited to one!")
    
    # Team creation
    if st.button("➕ Create New Team", use_container_width=True):
        st.session_state.show_team_creation = True
        st.session_state.show_profile = False  # Hide profile to show team creation
        st.rerun()

def show_team_creation():
    """Display team creation form"""
    st.title("🏢 Create New Team")
    
    # Check session state first
    if 'user' not in st.session_state or not st.session_state.user:
        st.error("❌ No user session found. Please log in again.")
        return
    
    # Cancel button
    if st.button("← Back to Profile", key="back_to_profile"):
        st.session_state.show_team_creation = False
        st.session_state.show_profile = True  # Show profile page
        st.rerun()
    
    st.markdown("---")
    
    # Quick team creation - no forms, just simple inputs
    st.subheader("Create Your Team")
    
    # Get current user info
    current_user = st.session_state.user
    st.info(f"Creating team for: {current_user.first_name} {current_user.last_name} ({current_user.user_id[:8]}...)")
    
    # Simple team creation with immediate execution
    col1, col2 = st.columns([3, 1])
    
    # Initialize team creation state if needed
    if 'team_creation_reset' not in st.session_state:
        st.session_state.team_creation_reset = 0
    
    with col1:
        # Use columns to create a simple form-like layout
        team_name = st.text_input(
            "Team Name",
            placeholder="Enter your team name",
            key=f"simple_team_name_{st.session_state.team_creation_reset}",
            help="Choose a descriptive name for your team"
        )
        
        team_desc = st.text_input(
            "Description (Optional)",
            placeholder="Brief description of your team",
            key=f"simple_team_desc_{st.session_state.team_creation_reset}"
        )
    
    with col2:
        st.write("")
        st.write("")
        if st.button("🚀 Create", type="primary", key="quick_create", use_container_width=True):
            if team_name and team_name.strip():
                try:
                    # Create team immediately
                    user_manager = st.session_state.user_manager
                    
                    team_id = user_manager.create_team(
                        name=team_name.strip(),
                        description=team_desc.strip() if team_desc else "",
                        owner_id=current_user.user_id
                    )
                    
                    # Show success
                    st.success(f"✅ Team '{team_name}' created successfully!")
                    st.info(f"Team ID: {team_id[:8]}...")
                    
                    # Clear the inputs by incrementing the reset counter
                    # This creates new widget keys, effectively clearing the inputs
                    st.session_state.team_creation_reset += 1
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
            else:
                st.error("⚠️ Please enter a team name")
    
    st.markdown("---")
    
    # Show current teams
    st.subheader("Your Teams")
    
    try:
        user_manager = st.session_state.user_manager
        teams = user_manager.get_user_teams(current_user.user_id)
        
        if teams:
            for i, team in enumerate(teams, 1):
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    st.write(f"**{i}. {team['name']}**")
                    if team.get('description'):
                        st.caption(team['description'])
                
                with col2:
                    st.write(f"Role: {team['user_role'].title()}")
                    st.caption(f"ID: {team['team_id'][:8]}...")
                
                with col3:
                    if team['user_role'] in ['owner', 'admin']:
                        if st.button("🛠️ Manage", key=f"mgmt_{team['team_id'][:8]}"):
                            st.session_state.selected_team = team['team_id']
                            st.session_state.show_team_management = True
                            st.session_state.show_team_creation = False
                            st.rerun()
        else:
            st.info("🏢 No teams yet. Create your first team above!")
    
    except Exception as e:
        st.error(f"Failed to load teams: {e}")
    
    # Quick debug info at the bottom
    with st.expander("🔧 Debug Info"):
        st.json({
            "user_id": current_user.user_id,
            "user_name": f"{current_user.first_name} {current_user.last_name}",
            "session_keys": [k for k in st.session_state.keys() if 'team' in k.lower()]
        })

def show_team_management():
    """Display team management interface"""
    team_id = st.session_state.selected_team
    user_manager = st.session_state.user_manager
    
    # Get team info
    teams = user_manager.get_user_teams(st.session_state.user.user_id)
    current_team = next((t for t in teams if t['team_id'] == team_id), None)
    
    if not current_team:
        st.error("Team not found")
        return
    
    st.title(f"🏢 Managing: {current_team['name']}")
    
    # Check permissions
    can_manage = current_team['user_role'] in ['owner', 'admin']
    
    if not can_manage:
        st.error("You don't have permission to manage this team")
        return
    
    # Team members
    st.markdown("### 👥 Team Members")
    
    members = user_manager.get_team_members(team_id)
    
    if members:
        for member in members:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    st.write(f"**{member['first_name']} {member['last_name']}**")
                    st.caption(f"{member['email']}")
                
                with col2:
                    st.write(f"Role: {member['team_role'].title()}")
                
                with col3:
                    st.write(f"Joined: {member['joined_at'][:10]}")
                
                with col4:
                    if member['team_role'] != 'owner' and current_team['user_role'] == 'owner':
                        if st.button("Remove", key=f"remove_{member['user_id']}"):
                            # TODO: Implement remove member
                            st.info("Remove member functionality coming soon")
    
    # Invite new members
    st.markdown("### ➕ Invite New Members")
    
    with st.form("invite_form"):
        email = st.text_input("Email Address", placeholder="colleague@company.com")
        role = st.selectbox("Role", ["Member", "Admin"], key="invite_role")
        
        invite_submitted = st.form_submit_button("📧 Send Invitation")
    
    if invite_submitted:
        if not email or not validate_email(email):
            st.error("Please enter a valid email address")
        else:
            role_mapping = {"Member": TeamRole.MEMBER, "Admin": TeamRole.ADMIN}
            team_role = role_mapping[role]
            
            success = user_manager.invite_user_to_team(
                team_id=team_id,
                user_email=email,
                role=team_role,
                invited_by=st.session_state.user.user_id
            )
            
            if success:
                st.success(f"✅ Invitation sent to {email}")
                st.rerun()
            else:
                st.error("Failed to send invitation. User may not exist or is already a member.")
    
    # Back button
    if st.button("← Back to Profile"):
        st.session_state.show_team_management = False
        st.rerun()

def show_logout_button():
    """Display logout button in sidebar"""
    with st.sidebar:
        st.markdown("---")
        
        user = st.session_state.user
        st.markdown(f"**Logged in as:** {user.first_name} {user.last_name}")
        st.caption(f"@{user.username}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("👤 Profile"):
                st.session_state.show_profile = True
                st.rerun()
        
        with col2:
            if st.button("🚪 Logout"):
                # Logout user
                if st.session_state.auth_token:
                    st.session_state.user_manager.logout_user(st.session_state.auth_token)
                
                # Clear session state
                st.session_state.user = None
                st.session_state.auth_token = None
                st.session_state.show_profile = False
                st.session_state.show_team_creation = False
                st.session_state.show_team_management = False
                
                st.success("Logged out successfully")
                st.rerun()

def require_authentication() -> bool:
    """Check if user is authenticated, show login if not"""
    init_auth_state()
    
    # Check if user is logged in
    if st.session_state.user and st.session_state.auth_token:
        # Verify token is still valid
        user_manager = st.session_state.user_manager
        user_id = user_manager.verify_token(st.session_state.auth_token)
        
        if user_id and user_id == st.session_state.user.user_id:
            return True
        else:
            # Token expired or invalid
            st.session_state.user = None
            st.session_state.auth_token = None
    
    # Show authentication UI
    if st.session_state.get('show_registration', False):
        show_registration_form()
    else:
        show_login_form()
    
    return False

def handle_authenticated_navigation():
    """Handle navigation for authenticated users"""
    # Check for profile/team management views
    if st.session_state.get('show_profile', False):
        show_user_profile()
        return True
    
    if st.session_state.get('show_team_creation', False):
        show_team_creation()
        return True
    
    if st.session_state.get('show_team_management', False):
        show_team_management()
        return True
    
    # Show logout button in sidebar
    show_logout_button()
    
    return False
