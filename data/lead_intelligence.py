#!/usr/bin/env python3
"""
Multi-Tenant Lead Intelligence System
Manages user-specific company datasets, team ICPs, and evolving lead intelligence
"""

import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
from pathlib import Path

class LeadStatus(Enum):
    """Lead lifecycle stages"""
    PROSPECT = "prospect"           # Initial research/scoring
    CONTACTED = "contacted"         # Outreach attempt made
    REPLIED = "replied"             # Lead responded
    QUALIFIED = "qualified"         # Meeting scheduled/lead qualified
    DEMO = "demo"                   # Demo/discovery call completed
    PROPOSAL = "proposal"           # Proposal/quote sent
    NEGOTIATION = "negotiation"     # In negotiation phase
    CLOSED_WON = "closed-won"       # Deal won
    CLOSED_LOST = "closed-lost"     # Deal lost
    NURTURING = "nurturing"         # Long-term nurture sequence

@dataclass
class CompanyRecord:
    """Core company information (deduplicated globally)"""
    company_id: str
    name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    employees: Optional[int] = None
    revenue: Optional[str] = None
    location: Optional[str] = None
    tech_stack: List[str] = None
    last_researched: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.tech_stack is None:
            self.tech_stack = []
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass 
class UserCompanyInteraction:
    """User-specific interaction with a company"""
    user_id: str
    company_id: str
    first_scored: datetime
    last_updated: datetime
    current_score: int
    status: LeadStatus
    personal_notes: str = ""
    team_notes: str = ""
    score_history: List[Dict] = None
    conversion_probability: Optional[float] = None
    next_action: Optional[str] = None
    
    def __post_init__(self):
        if self.score_history is None:
            self.score_history = []

@dataclass
class TeamICP:
    """Team-level Ideal Customer Profile"""
    icp_id: str
    team_id: str
    name: str
    description: str
    scoring_template: str
    success_patterns: Dict[str, Any]
    conversion_thresholds: Dict[str, float]
    active: bool = True
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class LeadIntelligenceDB:
    """Multi-tenant database for lead intelligence"""
    
    def __init__(self, db_path: str = "auth/users.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize the multi-tenant database schema"""
        conn = sqlite3.connect(self.db_path)
        
        # Core companies table (deduplicated globally)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                company_id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                domain TEXT,
                industry TEXT,
                employees INTEGER,
                revenue TEXT,
                location TEXT,
                tech_stack TEXT, -- JSON array
                last_researched DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # User-company interactions (user-specific views of companies)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_companies (
                user_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                first_scored DATETIME NOT NULL,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                current_score INTEGER NOT NULL,
                status TEXT NOT NULL,
                personal_notes TEXT DEFAULT '',
                team_notes TEXT DEFAULT '',
                score_history TEXT, -- JSON array of score records
                conversion_probability REAL,
                next_action TEXT,
                PRIMARY KEY (user_id, company_id),
                FOREIGN KEY (company_id) REFERENCES companies(company_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Team ICPs
        conn.execute("""
            CREATE TABLE IF NOT EXISTS team_icps (
                icp_id TEXT PRIMARY KEY,
                team_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                scoring_template TEXT NOT NULL,
                success_patterns TEXT, -- JSON
                conversion_thresholds TEXT, -- JSON  
                active BOOLEAN DEFAULT TRUE,
                created_by TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams(team_id),
                FOREIGN KEY (created_by) REFERENCES users(user_id)
            )
        """)
        
        # User personal ICPs (evolved from their successful patterns)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_icps (
                user_id TEXT PRIMARY KEY,
                scoring_weights TEXT, -- JSON of dimension weights
                successful_patterns TEXT, -- JSON of common traits in won deals
                preferred_industries TEXT, -- JSON array
                preferred_company_sizes TEXT, -- JSON array
                conversion_indicators TEXT, -- JSON of signals that predict success
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Lead scoring sessions (enhanced to track user context)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scoring_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                team_id TEXT,
                session_type TEXT, -- 'live_processing', 'batch_upload', 'manual_score'
                companies_processed INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                model_used TEXT,
                template_used TEXT,
                avg_score REAL,
                high_priority_count INTEGER,
                processing_time_seconds REAL,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (team_id) REFERENCES teams(team_id)
            )
        """)
        
        # Individual score records for detailed tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS score_records (
                record_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                score INTEGER NOT NULL,
                priority TEXT NOT NULL,
                justification TEXT,
                breakdown TEXT, -- JSON of dimension scores
                model_used TEXT,
                template_used TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES scoring_sessions(session_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (company_id) REFERENCES companies(company_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def upsert_company(self, company_data: Dict[str, Any]) -> str:
        """Insert or update company in global registry, return company_id"""
        conn = sqlite3.connect(self.db_path)
        
        # Check if company exists by name
        cursor = conn.execute(
            "SELECT company_id FROM companies WHERE name = ?", 
            (company_data['name'],)
        )
        existing = cursor.fetchone()
        
        if existing:
            company_id = existing[0]
            # Update last_researched and any new data
            conn.execute("""
                UPDATE companies 
                SET last_researched = CURRENT_TIMESTAMP,
                    domain = COALESCE(?, domain),
                    industry = COALESCE(?, industry),
                    tech_stack = COALESCE(?, tech_stack)
                WHERE company_id = ?
            """, (
                company_data.get('domain'),
                company_data.get('industry'), 
                json.dumps(company_data.get('tech_stack', [])),
                company_id
            ))
        else:
            company_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO companies (company_id, name, domain, industry, tech_stack, last_researched)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                company_id,
                company_data['name'],
                company_data.get('domain'),
                company_data.get('industry'),
                json.dumps(company_data.get('tech_stack', []))
            ))
        
        conn.commit()
        conn.close()
        return company_id
    
    def upsert_user_company_interaction(self, user_id: str, company_id: str, 
                                      score: int, status: LeadStatus = LeadStatus.PROSPECT,
                                      notes: str = "", breakdown: Dict = None) -> bool:
        """Create or update user's interaction with a company"""
        conn = sqlite3.connect(self.db_path)
        
        # Check if interaction exists
        cursor = conn.execute(
            "SELECT score_history FROM user_companies WHERE user_id = ? AND company_id = ?",
            (user_id, company_id)
        )
        existing = cursor.fetchone()
        
        score_record = {
            "timestamp": datetime.now().isoformat(),
            "score": score,
            "breakdown": breakdown or {},
            "model_used": "gpt-4o-mini"  # Would be passed in
        }
        
        if existing:
            # Update existing interaction
            current_history = json.loads(existing[0]) if existing[0] else []
            current_history.append(score_record)
            
            conn.execute("""
                UPDATE user_companies 
                SET current_score = ?, 
                    last_updated = CURRENT_TIMESTAMP,
                    status = ?,
                    personal_notes = ?,
                    score_history = ?
                WHERE user_id = ? AND company_id = ?
            """, (score, status.value, notes, json.dumps(current_history), user_id, company_id))
        else:
            # Create new interaction
            conn.execute("""
                INSERT INTO user_companies 
                (user_id, company_id, first_scored, current_score, status, personal_notes, score_history)
                VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?)
            """, (user_id, company_id, score, status.value, notes, json.dumps([score_record])))
        
        conn.commit()
        conn.close()
        return True
    
    def get_user_companies(self, user_id: str, requesting_user_id: str, 
                          permissions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get companies for a user based on permission level"""
        conn = sqlite3.connect(self.db_path)
        
        # Check permissions
        can_access = (
            permissions.get('is_manager', False) or 
            permissions.get('is_admin', False) or
            user_id == requesting_user_id or
            (permissions.get('is_team_lead', False) and 
             permissions.get('same_team', False))
        )
        
        if not can_access:
            conn.close()
            return []
        
        # Get user's company interactions with full company data
        query = """
            SELECT c.name, c.domain, c.industry, uc.current_score, uc.status,
                   uc.last_updated, uc.personal_notes, uc.score_history,
                   uc.conversion_probability, uc.next_action, c.company_id
            FROM user_companies uc
            JOIN companies c ON uc.company_id = c.company_id
            WHERE uc.user_id = ?
            ORDER BY uc.last_updated DESC
        """
        
        df = pd.read_sql_query(query, conn, params=(user_id,))
        conn.close()
        
        # Convert to list of dicts and parse JSON fields
        results = []
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            if row_dict['score_history']:
                row_dict['score_history'] = json.loads(row_dict['score_history'])
            results.append(row_dict)
        
        return results
    
    def get_team_companies(self, team_id: str, requesting_user_id: str,
                          permissions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get all companies processed by team members"""
        conn = sqlite3.connect(self.db_path)
        
        # Only team leads, managers, or admins can see team-wide data
        can_access = (
            permissions.get('is_manager', False) or 
            permissions.get('is_admin', False) or
            permissions.get('is_team_lead', False)
        )
        
        if not can_access:
            conn.close()
            return []
        
        # Get team members' company interactions
        query = """
            SELECT c.name, c.domain, c.industry, 
                   COUNT(uc.user_id) as users_scored,
                   AVG(uc.current_score) as avg_score,
                   MAX(uc.last_updated) as last_activity,
                   GROUP_CONCAT(u.first_name || ' ' || u.last_name) as scored_by,
                   c.company_id
            FROM user_companies uc
            JOIN companies c ON uc.company_id = c.company_id
            JOIN users u ON uc.user_id = u.user_id
            JOIN team_memberships tm ON u.user_id = tm.user_id
            WHERE tm.team_id = ? AND tm.is_active = TRUE
            GROUP BY c.company_id, c.name, c.domain, c.industry
            ORDER BY avg_score DESC
        """
        
        df = pd.read_sql_query(query, conn, params=(team_id,))
        conn.close()
        
        return df.to_dict('records')

class LeadIntelligenceEngine:
    """Main engine for managing multi-tenant lead intelligence"""
    
    def __init__(self, db_path: str = "auth/users.db"):
        self.db = LeadIntelligenceDB(db_path)
    
    def record_scoring_session(self, user_id: str, team_id: str, 
                             scored_results: List[Dict[str, Any]], 
                             session_type: str = "live_processing",
                             model_used: str = "gpt-4o-mini") -> str:
        """Record a scoring session and update user's company dataset"""
        
        session_id = str(uuid.uuid4())
        session_start = datetime.now()
        
        # Process each scored company
        companies_processed = 0
        total_score = 0
        high_priority_count = 0
        
        for result in scored_results:
            if 'company' not in result or not result.get('score'):
                continue
                
            # 1. Upsert company to global registry
            company_data = {
                'name': result['company'],
                'domain': result.get('domain'),
                'industry': result.get('industry'),
                'tech_stack': result.get('tech_stack', [])
            }
            company_id = self.db.upsert_company(company_data)
            
            # 2. Update user's interaction with this company
            status = LeadStatus.PROSPECT  # Default, but could be inferred
            breakdown = result.get('breakdown', {})
            
            self.db.upsert_user_company_interaction(
                user_id=user_id,
                company_id=company_id,
                score=result['score'],
                status=status,
                breakdown=breakdown
            )
            
            # 3. Record detailed score record
            self._record_score_detail(
                session_id=session_id,
                user_id=user_id, 
                company_id=company_id,
                result=result,
                model_used=model_used
            )
            
            companies_processed += 1
            total_score += result['score']
            if result.get('priority') == 'High':
                high_priority_count += 1
        
        # Record the session
        avg_score = total_score / companies_processed if companies_processed > 0 else 0
        processing_time = (datetime.now() - session_start).total_seconds()
        
        self._record_session(
            session_id=session_id,
            user_id=user_id,
            team_id=team_id,
            session_type=session_type,
            companies_processed=companies_processed,
            avg_score=avg_score,
            high_priority_count=high_priority_count,
            processing_time=processing_time,
            model_used=model_used
        )
        
        return session_id
    
    def _record_session(self, session_id: str, user_id: str, team_id: str,
                       session_type: str, companies_processed: int, avg_score: float,
                       high_priority_count: int, processing_time: float, model_used: str):
        """Record session metadata"""
        conn = sqlite3.connect(self.db.db_path)
        
        conn.execute("""
            INSERT INTO scoring_sessions 
            (session_id, user_id, team_id, session_type, companies_processed, 
             avg_score, high_priority_count, processing_time_seconds, model_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, user_id, team_id, session_type, companies_processed,
              avg_score, high_priority_count, processing_time, model_used))
        
        conn.commit()
        conn.close()
    
    def _record_score_detail(self, session_id: str, user_id: str, company_id: str,
                           result: Dict[str, Any], model_used: str):
        """Record detailed scoring information"""
        conn = sqlite3.connect(self.db.db_path)
        
        record_id = str(uuid.uuid4())
        
        conn.execute("""
            INSERT INTO score_records
            (record_id, session_id, user_id, company_id, score, priority,
             justification, breakdown, model_used, template_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record_id, session_id, user_id, company_id,
            result['score'], result.get('priority', 'Medium'),
            result.get('justification', ''), 
            json.dumps(result.get('breakdown', {})),
            model_used, result.get('template_used', 'recurly_template')
        ))
        
        conn.commit()
        conn.close()
    
    def update_lead_status(self, user_id: str, company_name: str, 
                          new_status: LeadStatus, notes: str = "") -> bool:
        """Update the status of a lead in user's pipeline"""
        conn = sqlite3.connect(self.db.db_path)
        
        # Get company_id from name
        cursor = conn.execute("SELECT company_id FROM companies WHERE name = ?", (company_name,))
        company_row = cursor.fetchone()
        
        if not company_row:
            conn.close()
            return False
        
        company_id = company_row[0]
        
        # Update user's interaction
        cursor = conn.execute("""
            UPDATE user_companies 
            SET status = ?, 
                personal_notes = ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE user_id = ? AND company_id = ?
        """, (new_status.value, notes, user_id, company_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def get_user_pipeline(self, user_id: str, status_filter: Optional[LeadStatus] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """Get user's current lead pipeline with status filtering"""
        conn = sqlite3.connect(self.db.db_path)
        
        query = """
            SELECT c.name, c.domain, c.industry, uc.current_score, 
                   uc.status, uc.last_updated, uc.personal_notes,
                   uc.conversion_probability, uc.next_action
            FROM user_companies uc
            JOIN companies c ON uc.company_id = c.company_id
            WHERE uc.user_id = ?
        """
        params = [user_id]
        
        if status_filter:
            query += " AND uc.status = ?"
            params.append(status_filter.value)
        
        query += " ORDER BY uc.current_score DESC, uc.last_updated DESC LIMIT ?"
        params.append(limit)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df.to_dict('records')
    
    def get_user_performance_summary(self, user_id: str, days_back: int = 30) -> Dict[str, Any]:
        """Get performance summary for a user"""
        conn = sqlite3.connect(self.db.db_path)
        
        # Session metrics
        session_query = """
            SELECT COUNT(*) as total_sessions,
                   SUM(companies_processed) as total_companies,
                   AVG(avg_score) as avg_score,
                   SUM(high_priority_count) as high_priority_total
            FROM scoring_sessions
            WHERE user_id = ? AND timestamp >= datetime('now', '-{} days')
        """.format(days_back)
        
        session_metrics = pd.read_sql_query(session_query, conn, params=(user_id,)).iloc[0].to_dict()
        
        # Pipeline metrics
        pipeline_query = """
            SELECT status, COUNT(*) as count
            FROM user_companies
            WHERE user_id = ?
            GROUP BY status
        """
        
        pipeline_df = pd.read_sql_query(pipeline_query, conn, params=(user_id,))
        pipeline_metrics = dict(zip(pipeline_df['status'], pipeline_df['count']))
        
        conn.close()
        
        return {
            'session_metrics': session_metrics,
            'pipeline_metrics': pipeline_metrics,
            'total_in_pipeline': sum(pipeline_metrics.values()),
            'conversion_rate': pipeline_metrics.get('closed-won', 0) / max(sum(pipeline_metrics.values()), 1)
        }

class DataAccessController:
    """Controls data access based on user roles and team membership"""
    
    def __init__(self, user_manager, lead_intelligence_engine):
        self.user_manager = user_manager
        self.intelligence = lead_intelligence_engine
    
    def get_user_permissions(self, requesting_user_id: str, target_user_id: str) -> Dict[str, bool]:
        """Determine what data the requesting user can access about the target user"""
        
        requesting_user = self.user_manager.get_user(requesting_user_id)
        target_user = self.user_manager.get_user(target_user_id)
        
        if not requesting_user or not target_user:
            return {'can_access': False}
        
        # Get team relationships
        requesting_teams = self.user_manager.get_user_teams(requesting_user_id)
        target_teams = self.user_manager.get_user_teams(target_user_id)
        
        requesting_team_ids = {t['team_id'] for t in requesting_teams}
        target_team_ids = {t['team_id'] for t in target_teams}
        
        # Check if same team
        same_team = bool(requesting_team_ids.intersection(target_team_ids))
        
        # Check if requesting user is team lead of any shared team
        is_team_lead = any(
            t['user_role'] in ['owner', 'admin'] 
            for t in requesting_teams 
            if t['team_id'] in target_team_ids
        )
        
        return {
            'can_access': True,
            'is_manager': requesting_user.role.value == 'manager',
            'is_admin': requesting_user.role.value == 'manager',  # For now, manager is highest role
            'is_team_lead': is_team_lead,
            'same_team': same_team,
            'is_self': requesting_user_id == target_user_id
        }

if __name__ == "__main__":
    # Demo usage
    intelligence = LeadIntelligenceEngine()
    
    # Simulate recording a scoring session
    demo_results = [
        {
            "company": "TestCorp",
            "domain": "testcorp.com", 
            "score": 87,
            "priority": "High",
            "breakdown": {"industry_fit": 18, "scale_indicators": 17}
        }
    ]
    
    session_id = intelligence.record_scoring_session(
        user_id="test-user-123",
        team_id="test-team-456", 
        scored_results=demo_results,
        session_type="demo"
    )
    
    print(f"Recorded session: {session_id}")
    
    # Get user's pipeline
    pipeline = intelligence.get_user_pipeline("test-user-123")
    print(f"User pipeline: {len(pipeline)} companies")
    
    # Get performance summary
    performance = intelligence.get_user_performance_summary("test-user-123")
    print(f"Performance: {json.dumps(performance, indent=2)}")
