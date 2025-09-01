#!/usr/bin/env python3
"""
User Management and Authentication System for Recursor
Handles user registration, authentication, sessions, and team management
"""

import hashlib
import secrets
import sqlite3
import jwt
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import bcrypt
import uuid

class UserRole(Enum):
    ADMIN = "admin"
    TEAM_LEAD = "team_lead"
    ANALYST = "analyst"
    VIEWER = "viewer"

class TeamRole(Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"

@dataclass
class User:
    """User model with authentication and profile information"""
    user_id: str
    email: str
    username: str
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    profile_picture: Optional[str] = None
    preferences: Optional[Dict] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['role'] = self.role.value
        data['created_at'] = self.created_at.isoformat()
        data['last_login'] = self.last_login.isoformat() if self.last_login else None
        return data

@dataclass  
class Team:
    """Team model for organizing users and data"""
    team_id: str
    name: str
    description: str
    owner_id: str
    is_active: bool
    created_at: datetime
    settings: Optional[Dict] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data

@dataclass
class TeamMembership:
    """Association between users and teams"""
    membership_id: str
    user_id: str
    team_id: str
    role: TeamRole
    joined_at: datetime
    invited_by: str
    permissions: Optional[Dict] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['role'] = self.role.value
        data['joined_at'] = self.joined_at.isoformat()
        return data

class UserManager:
    """Comprehensive user management system"""
    
    def __init__(self, db_path: str = "auth/users.db", jwt_secret: Optional[str] = None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.jwt_secret = jwt_secret or self._get_or_create_secret()
        self._init_database()
    
    def _get_or_create_secret(self) -> str:
        """Get or create JWT secret key"""
        secret_file = self.db_path.parent / ".jwt_secret"
        if secret_file.exists():
            return secret_file.read_text().strip()
        else:
            secret = secrets.token_urlsafe(32)
            secret_file.write_text(secret)
            secret_file.chmod(0o600)  # Restrict permissions
            return secret
    
    def _init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        
        # Users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'analyst',
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME,
                profile_picture TEXT,
                preferences TEXT,
                email_verified BOOLEAN DEFAULT FALSE,
                reset_token TEXT,
                reset_token_expires DATETIME
            )
        """)
        
        # Teams table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                team_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                owner_id TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                settings TEXT,
                FOREIGN KEY (owner_id) REFERENCES users (user_id)
            )
        """)
        
        # Team memberships table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS team_memberships (
                membership_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                team_id TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                invited_by TEXT NOT NULL,
                permissions TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (team_id) REFERENCES teams (team_id),
                FOREIGN KEY (invited_by) REFERENCES users (user_id),
                UNIQUE(user_id, team_id)
            )
        """)
        
        # Sessions table for active user sessions
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Audit log table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                log_id TEXT PRIMARY KEY,
                user_id TEXT,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                details TEXT,
                ip_address TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def create_user(
        self,
        email: str,
        username: str,
        password: str,
        first_name: str,
        last_name: str,
        role: UserRole = UserRole.ANALYST
    ) -> str:
        """Create new user account"""
        
        # Validation
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not email or '@' not in email:
            raise ValueError("Valid email address is required")
        
        user_id = str(uuid.uuid4())
        password_hash = self.hash_password(password)
        
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT INTO users (user_id, email, username, password_hash, first_name, last_name, role)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, email, username, password_hash, first_name, last_name, role.value))
            
            conn.commit()
            
            # Log user creation
            self._log_action(user_id, "user_created", "user", user_id, {"email": email, "username": username})
            
            return user_id
            
        except sqlite3.IntegrityError as e:
            if "email" in str(e):
                raise ValueError("Email address already registered")
            elif "username" in str(e):
                raise ValueError("Username already taken")
            else:
                raise ValueError("User creation failed")
        finally:
            conn.close()
    
    def authenticate_user(self, email: str, password: str, ip_address: Optional[str] = None) -> Optional[str]:
        """Authenticate user and return JWT token"""
        conn = sqlite3.connect(self.db_path)
        
        # Get user data
        cursor = conn.execute("""
            SELECT user_id, password_hash, is_active FROM users WHERE email = ?
        """, (email,))
        
        result = cursor.fetchone()
        if not result:
            return None
        
        user_id, password_hash, is_active = result
        
        if not is_active:
            raise ValueError("Account is deactivated")
        
        if not self.verify_password(password, password_hash):
            return None
        
        # Update last login
        conn.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        # Generate JWT token
        token = self._generate_token(user_id)
        
        # Store session
        self._create_session(user_id, token, ip_address)
        
        # Log successful login
        self._log_action(user_id, "user_login", "session", None, {"ip_address": ip_address})
        
        return token
    
    def _generate_token(self, user_id: str, expires_hours: int = 24) -> str:
        """Generate JWT token for user"""
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=expires_hours),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
    def verify_token(self, token: str) -> Optional[str]:
        """Verify JWT token and return user_id"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            user_id = payload.get('user_id')
            
            # Check if session is still active
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("""
                SELECT is_active FROM user_sessions 
                WHERE user_id = ? AND token_hash = ? AND expires_at > CURRENT_TIMESTAMP
            """, (user_id, hashlib.sha256(token.encode()).hexdigest()))
            
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                return user_id
            else:
                return None
                
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def _create_session(self, user_id: str, token: str, ip_address: Optional[str] = None):
        """Create user session record"""
        session_id = str(uuid.uuid4())
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO user_sessions (session_id, user_id, token_hash, expires_at, ip_address)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, user_id, token_hash, expires_at, ip_address))
        conn.commit()
        conn.close()
    
    def logout_user(self, token: str):
        """Logout user by invalidating session"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE user_sessions SET is_active = FALSE WHERE token_hash = ?
        """, (token_hash,))
        conn.commit()
        conn.close()
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT user_id, email, username, first_name, last_name, role, is_active, 
                   created_at, last_login, profile_picture, preferences
            FROM users WHERE user_id = ?
        """, (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        return User(
            user_id=result[0],
            email=result[1],
            username=result[2],
            first_name=result[3],
            last_name=result[4],
            role=UserRole(result[5]),
            is_active=bool(result[6]),
            created_at=datetime.fromisoformat(result[7]),
            last_login=datetime.fromisoformat(result[8]) if result[8] else None,
            profile_picture=result[9],
            preferences=eval(result[10]) if result[10] else None
        )
    
    def create_team(self, name: str, description: str, owner_id: str) -> str:
        """Create new team"""
        team_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        
        # Create team
        conn.execute("""
            INSERT INTO teams (team_id, name, description, owner_id)
            VALUES (?, ?, ?, ?)
        """, (team_id, name, description, owner_id))
        
        # Add owner as team member with owner role
        membership_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO team_memberships (membership_id, user_id, team_id, role, invited_by)
            VALUES (?, ?, ?, ?, ?)
        """, (membership_id, owner_id, team_id, TeamRole.OWNER.value, owner_id))
        
        conn.commit()
        conn.close()
        
        # Log team creation
        self._log_action(owner_id, "team_created", "team", team_id, {"name": name})
        
        return team_id
    
    def invite_user_to_team(self, team_id: str, user_email: str, role: TeamRole, invited_by: str) -> bool:
        """Invite user to team by email"""
        conn = sqlite3.connect(self.db_path)
        
        # Get user_id from email
        cursor = conn.execute("SELECT user_id FROM users WHERE email = ? AND is_active = TRUE", (user_email,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False
        
        user_id = result[0]
        
        # Check if user is already a member
        cursor = conn.execute("""
            SELECT membership_id FROM team_memberships 
            WHERE user_id = ? AND team_id = ? AND is_active = TRUE
        """, (user_id, team_id))
        
        if cursor.fetchone():
            conn.close()
            return False  # Already a member
        
        # Add team membership
        membership_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO team_memberships (membership_id, user_id, team_id, role, invited_by)
            VALUES (?, ?, ?, ?, ?)
        """, (membership_id, user_id, team_id, role.value, invited_by))
        
        conn.commit()
        conn.close()
        
        # Log team invitation
        self._log_action(invited_by, "user_invited", "team", team_id, 
                        {"invited_user": user_email, "role": role.value})
        
        return True
    
    def get_user_teams(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all teams for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT t.team_id, t.name, t.description, t.owner_id, t.created_at,
                   tm.role, tm.joined_at
            FROM teams t
            JOIN team_memberships tm ON t.team_id = tm.team_id
            WHERE tm.user_id = ? AND tm.is_active = TRUE AND t.is_active = TRUE
            ORDER BY tm.joined_at DESC
        """, (user_id,))
        
        teams = []
        for row in cursor.fetchall():
            teams.append({
                'team_id': row[0],
                'name': row[1],
                'description': row[2],
                'owner_id': row[3],
                'created_at': row[4],
                'user_role': row[5],
                'joined_at': row[6]
            })
        
        conn.close()
        return teams
    
    def get_team_members(self, team_id: str) -> List[Dict[str, Any]]:
        """Get all members of a team"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT u.user_id, u.email, u.username, u.first_name, u.last_name,
                   tm.role, tm.joined_at, tm.invited_by
            FROM users u
            JOIN team_memberships tm ON u.user_id = tm.user_id
            WHERE tm.team_id = ? AND tm.is_active = TRUE AND u.is_active = TRUE
            ORDER BY tm.joined_at ASC
        """, (team_id,))
        
        members = []
        for row in cursor.fetchall():
            members.append({
                'user_id': row[0],
                'email': row[1],
                'username': row[2],
                'first_name': row[3],
                'last_name': row[4],
                'team_role': row[5],
                'joined_at': row[6],
                'invited_by': row[7]
            })
        
        conn.close()
        return members
    
    def check_team_permission(self, user_id: str, team_id: str, required_role: TeamRole = TeamRole.MEMBER) -> bool:
        """Check if user has required permissions for team"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT role FROM team_memberships 
            WHERE user_id = ? AND team_id = ? AND is_active = TRUE
        """, (user_id, team_id))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False
        
        user_role = TeamRole(result[0])
        
        # Define role hierarchy
        role_hierarchy = {
            TeamRole.GUEST: 1,
            TeamRole.MEMBER: 2,
            TeamRole.ADMIN: 3,
            TeamRole.OWNER: 4
        }
        
        return role_hierarchy[user_role] >= role_hierarchy[required_role]
    
    def _log_action(self, user_id: str, action: str, resource_type: str, 
                   resource_id: Optional[str], details: Optional[Dict] = None):
        """Log user action for audit trail"""
        log_id = str(uuid.uuid4())
        details_json = str(details) if details else None
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO audit_log (log_id, user_id, action, resource_type, resource_id, details)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (log_id, user_id, action, resource_type, resource_id, details_json))
        conn.commit()
        conn.close()
    
    def get_audit_log(self, user_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit log entries"""
        conn = sqlite3.connect(self.db_path)
        
        if user_id:
            cursor = conn.execute("""
                SELECT al.*, u.username, u.first_name, u.last_name
                FROM audit_log al
                LEFT JOIN users u ON al.user_id = u.user_id
                WHERE al.user_id = ?
                ORDER BY al.timestamp DESC
                LIMIT ?
            """, (user_id, limit))
        else:
            cursor = conn.execute("""
                SELECT al.*, u.username, u.first_name, u.last_name
                FROM audit_log al
                LEFT JOIN users u ON al.user_id = u.user_id
                ORDER BY al.timestamp DESC
                LIMIT ?
            """, (limit,))
        
        logs = []
        for row in cursor.fetchall():
            logs.append({
                'log_id': row[0],
                'user_id': row[1],
                'action': row[2],
                'resource_type': row[3],
                'resource_id': row[4],
                'details': row[5],
                'ip_address': row[6],
                'timestamp': row[7],
                'username': row[8],
                'first_name': row[9],
                'last_name': row[10]
            })
        
        conn.close()
        return logs

# Streamlit session state helper functions
def get_current_user() -> Optional[User]:
    """Get current user from Streamlit session state"""
    import streamlit as st
    return st.session_state.get('user')

def require_auth():
    """Decorator to require authentication"""
    import streamlit as st
    
    if 'user' not in st.session_state or not st.session_state.user:
        st.error("Please log in to access this feature")
        st.stop()

def require_team_permission(team_id: str, role: TeamRole = TeamRole.MEMBER):
    """Require specific team permissions"""
    import streamlit as st
    
    require_auth()
    user_manager = UserManager()
    
    if not user_manager.check_team_permission(st.session_state.user.user_id, team_id, role):
        st.error("You don't have permission to access this resource")
        st.stop()
