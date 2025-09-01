#!/usr/bin/env python3
"""
Multi-Tenant Analytics Extension for Recursor
Extends team analytics with user/team-based data isolation and permissions
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from analytics.team_analytics import TeamAnalyticsEngine, ProcessingSession, LeadAnalytics
from auth.user_manager import UserManager, TeamRole
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

class MultiTenantAnalyticsEngine(TeamAnalyticsEngine):
    """Multi-tenant analytics engine with team-based data isolation"""
    
    def __init__(self, db_path: str = "analytics/team_analytics.db"):
        super().__init__(db_path)
        self.user_manager = UserManager()
        self._extend_schema_for_multitenancy()
    
    def _extend_schema_for_multitenancy(self):
        """Extend existing schema with team-based fields"""
        conn = sqlite3.connect(self.db.db_path)
        
        # Add team_id to sessions table if it doesn't exist
        cursor = conn.execute("PRAGMA table_info(sessions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'team_id' not in columns:
            conn.execute("ALTER TABLE sessions ADD COLUMN team_id TEXT")
            conn.execute("ALTER TABLE sessions ADD COLUMN created_by TEXT")
        
        # Add team_id to leads table if it doesn't exist
        cursor = conn.execute("PRAGMA table_info(leads)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'team_id' not in columns:
            conn.execute("ALTER TABLE leads ADD COLUMN team_id TEXT")
        
        # Create team analytics summary table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS team_analytics_summary (
                summary_id TEXT PRIMARY KEY,
                team_id TEXT NOT NULL,
                date DATE NOT NULL,
                total_sessions INTEGER DEFAULT 0,
                total_leads INTEGER DEFAULT 0,
                avg_score REAL DEFAULT 0,
                high_priority_count INTEGER DEFAULT 0,
                unique_users INTEGER DEFAULT 0,
                processing_time_total REAL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(team_id, date)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def record_processing_session(
        self, 
        results: List[Dict[str, Any]], 
        user: str = "system",
        team_id: Optional[str] = None,
        input_file: str = "unknown",
        processing_time: float = 0.0,
        model_used: str = "gpt-4-turbo",
        template_used: str = "recurly_template.txt",
        clusters: Optional[Dict] = None
    ) -> str:
        """Record processing session with team isolation"""
        
        # Create session manually to handle extended schema
        import uuid
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user}_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now()
        
        # Calculate session metrics
        total_leads = len(results)
        processed_leads = sum(1 for r in results if 'score' in r and r.get('score', 0) > 0)
        success_rate = processed_leads / total_leads if total_leads > 0 else 0
        
        import numpy as np
        avg_score = np.mean([r.get('score', 0) for r in results if 'score' in r])
        high_priority_count = sum(1 for r in results if r.get('priority') == 'High')
        
        # Clustering metrics
        clustering_enabled = clusters is not None
        clusters_created = len(clusters) if clusters else 0
        
        # Save session with extended schema
        conn = sqlite3.connect(self.db.db_path)
        conn.execute("""
            INSERT INTO sessions (
                session_id, user, timestamp, input_file, total_leads, processed_leads, 
                success_rate, avg_score, high_priority_count, processing_time, 
                model_used, template_used, clustering_enabled, clusters_created,
                team_id, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id, user, timestamp, input_file, total_leads, processed_leads,
            success_rate, avg_score, high_priority_count, processing_time,
            model_used, template_used, clustering_enabled, clusters_created,
            team_id, user
        ))
        
        conn.commit()
        conn.close()
        
        # Create and save lead analytics
        lead_analytics = []
        for result in results:
            if 'company' not in result:
                continue
                
            # Extract breakdown scores
            breakdown = result.get('breakdown', {})
            
            lead = LeadAnalytics(
                company=result.get('company', ''),
                domain=result.get('domain', ''),
                score=result.get('score', 0),
                priority=result.get('priority', 'Low'),
                industry_fit=breakdown.get('industry_fit', 0),
                scale_indicators=breakdown.get('scale_indicators', 0),
                platform_maturity=breakdown.get('platform_maturity', 0),
                growth_churn_challenges=breakdown.get('growth_churn_challenges', 0),
                revenue_sophistication=breakdown.get('revenue_sophistication', 0),
                processing_time=processing_time / total_leads if total_leads > 0 else 0,
                session_id=session_id,
                timestamp=timestamp,
                cluster_id=result.get('cluster_id'),
                cluster_label=result.get('cluster_label')
            )
            lead_analytics.append(lead)
        
        # Save leads with team_id
        conn = sqlite3.connect(self.db.db_path)
        for lead in lead_analytics:
            conn.execute("""
                INSERT INTO leads (
                    company, domain, score, priority, industry_fit, scale_indicators,
                    platform_maturity, growth_churn_challenges, revenue_sophistication,
                    processing_time, session_id, timestamp, cluster_id, cluster_label, team_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lead.company, lead.domain, lead.score, lead.priority,
                lead.industry_fit, lead.scale_indicators, lead.platform_maturity,
                lead.growth_churn_challenges, lead.revenue_sophistication,
                lead.processing_time, lead.session_id, lead.timestamp,
                lead.cluster_id, lead.cluster_label, team_id
            ))
        
        conn.commit()
        conn.close()
        
        # Update team analytics summary if team provided
        if team_id:
            self._update_team_summary(team_id, datetime.now().date())
        
        return session_id
    
    def _update_team_summary(self, team_id: str, date: datetime.date):
        """Update daily team analytics summary"""
        conn = sqlite3.connect(self.db.db_path)
        
        # Calculate daily metrics for team
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as session_count,
                SUM(processed_leads) as total_leads,
                AVG(avg_score) as avg_score,
                SUM(high_priority_count) as high_priority_count,
                COUNT(DISTINCT user) as unique_users,
                SUM(processing_time) as total_processing_time
            FROM sessions 
            WHERE team_id = ? AND DATE(timestamp) = ?
        """, (team_id, date))
        
        result = cursor.fetchone()
        
        if result and result[0] > 0:
            # Insert or update summary
            summary_id = f"{team_id}_{date}"
            conn.execute("""
                INSERT OR REPLACE INTO team_analytics_summary 
                (summary_id, team_id, date, total_sessions, total_leads, avg_score, 
                 high_priority_count, unique_users, processing_time_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (summary_id, team_id, date, result[0], result[1] or 0, result[2] or 0,
                  result[3] or 0, result[4] or 0, result[5] or 0))
        
        conn.commit()
        conn.close()
    
    def get_team_performance_metrics(self, team_id: str, days_back: int = 30) -> Dict[str, Any]:
        """Get team-specific performance metrics"""
        
        # Verify team access
        sessions_df = self.db.get_sessions(days_back)
        if not sessions_df.empty:
            # Filter by team_id
            team_sessions = sessions_df[sessions_df['team_id'] == team_id] if 'team_id' in sessions_df.columns else sessions_df
        else:
            team_sessions = sessions_df
        
        leads_df = self.db.get_leads(days_back)
        if not leads_df.empty:
            team_leads = leads_df[leads_df['team_id'] == team_id] if 'team_id' in leads_df.columns else leads_df
        else:
            team_leads = leads_df
        
        if team_sessions.empty:
            return {"error": "No data available for this team"}
        
        metrics = {}
        
        # Overall metrics
        metrics['total_sessions'] = len(team_sessions)
        metrics['total_leads_processed'] = team_sessions['processed_leads'].sum()
        metrics['avg_success_rate'] = team_sessions['success_rate'].mean()
        metrics['avg_processing_time'] = team_sessions['processing_time'].mean()
        metrics['total_high_priority'] = team_sessions['high_priority_count'].sum()
        
        # User metrics (team members only)
        user_metrics = team_sessions.groupby('user').agg({
            'session_id': 'count',
            'processed_leads': 'sum',
            'success_rate': 'mean',
            'avg_score': 'mean',
            'high_priority_count': 'sum'
        }).to_dict('index')
        metrics['user_performance'] = user_metrics
        
        # Model performance
        model_metrics = team_sessions.groupby('model_used').agg({
            'avg_score': 'mean',
            'success_rate': 'mean',
            'processing_time': 'mean',
            'session_id': 'count'
        }).to_dict('index')
        metrics['model_performance'] = model_metrics
        
        # Template performance
        template_metrics = team_sessions.groupby('template_used').agg({
            'avg_score': 'mean',
            'success_rate': 'mean',
            'session_id': 'count'
        }).to_dict('index')
        metrics['template_performance'] = template_metrics
        
        # Time-based trends
        team_sessions['date'] = team_sessions['timestamp'].dt.date
        daily_metrics = team_sessions.groupby('date').agg({
            'processed_leads': 'sum',
            'avg_score': 'mean',
            'success_rate': 'mean',
            'high_priority_count': 'sum'
        }).to_dict('list')
        metrics['daily_trends'] = daily_metrics
        
        return metrics
    
    def get_team_lead_insights(self, team_id: str, days_back: int = 30) -> Dict[str, Any]:
        """Get team-specific lead insights"""
        leads_df = self.db.get_leads(days_back)
        
        if leads_df.empty:
            return {"error": "No lead data available"}
        
        # Filter by team
        if 'team_id' in leads_df.columns:
            team_leads = leads_df[leads_df['team_id'] == team_id]
        else:
            team_leads = leads_df
        
        if team_leads.empty:
            return {"error": "No lead data available for this team"}
        
        insights = {}
        
        # Score distribution
        insights['score_distribution'] = {
            'high': len(team_leads[team_leads['score'] >= 75]),
            'medium': len(team_leads[(team_leads['score'] >= 50) & (team_leads['score'] < 75)]),
            'low': len(team_leads[team_leads['score'] < 50])
        }
        
        # Priority distribution
        insights['priority_distribution'] = team_leads['priority'].value_counts().to_dict()
        
        # Dimension analysis
        dimension_cols = ['industry_fit', 'scale_indicators', 'platform_maturity', 
                         'growth_churn_challenges', 'revenue_sophistication']
        
        dimension_stats = {}
        for dim in dimension_cols:
            dimension_stats[dim] = {
                'mean': team_leads[dim].mean(),
                'std': team_leads[dim].std(),
                'correlation_with_score': team_leads[dim].corr(team_leads['score'])
            }
        insights['dimension_analysis'] = dimension_stats
        
        # Top performing companies (team-specific)
        top_companies = team_leads.nlargest(10, 'score')[['company', 'score', 'priority']].to_dict('records')
        insights['top_companies'] = top_companies
        
        return insights
    
    def create_team_performance_charts(self, team_id: str, days_back: int = 30) -> Dict[str, go.Figure]:
        """Create team-specific performance charts"""
        metrics = self.get_team_performance_metrics(team_id, days_back)
        insights = self.get_team_lead_insights(team_id, days_back)
        
        charts = {}
        
        # 1. Daily trends chart
        if 'daily_trends' in metrics and metrics['daily_trends']:
            dates = list(metrics['daily_trends'].keys())
            leads_processed = metrics['daily_trends']['processed_leads']
            avg_scores = metrics['daily_trends']['avg_score']
            
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Daily Leads Processed', 'Average Daily Scores'),
                vertical_spacing=0.1
            )
            
            fig.add_trace(
                go.Bar(x=dates, y=leads_processed, name="Leads Processed"),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(x=dates, y=avg_scores, mode='lines+markers', name="Avg Score"),
                row=2, col=1
            )
            
            fig.update_layout(height=600, title_text="Team Performance Trends")
            charts['daily_trends'] = fig
        
        # 2. Team member performance comparison
        if 'user_performance' in metrics:
            users = list(metrics['user_performance'].keys())
            sessions = [metrics['user_performance'][u]['session_id'] for u in users]
            avg_scores = [metrics['user_performance'][u]['avg_score'] for u in users]
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=users,
                y=sessions,
                name="Sessions",
                yaxis="y"
            ))
            
            fig.add_trace(go.Scatter(
                x=users,
                y=avg_scores,
                mode='lines+markers',
                name="Avg Score",
                yaxis="y2"
            ))
            
            fig.update_layout(
                title="Team Member Performance Comparison",
                yaxis=dict(title="Number of Sessions", side="left"),
                yaxis2=dict(title="Average Score", side="right", overlaying="y"),
                hovermode="x"
            )
            charts['user_performance'] = fig
        
        # 3. Team score distribution
        if 'score_distribution' in insights:
            labels = ['High (75+)', 'Medium (50-74)', 'Low (<50)']
            values = [insights['score_distribution']['high'],
                     insights['score_distribution']['medium'],
                     insights['score_distribution']['low']]
            colors = ['#28a745', '#ffc107', '#dc3545']
            
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                marker_colors=colors,
                textinfo='label+percent+value'
            )])
            fig.update_layout(title="Team Lead Score Distribution")
            charts['score_distribution'] = fig
        
        return charts
    
    def get_cross_team_comparison(self, user_id: str, days_back: int = 30) -> Dict[str, Any]:
        """Compare performance across teams user has access to"""
        
        # Get user's teams
        teams = self.user_manager.get_user_teams(user_id)
        
        if not teams:
            return {"error": "User is not part of any teams"}
        
        comparison = {
            'teams': [],
            'summary': {
                'total_teams': len(teams),
                'total_sessions': 0,
                'total_leads': 0,
                'best_performing_team': None,
                'most_active_team': None
            }
        }
        
        best_score = 0
        most_sessions = 0
        
        for team in teams:
            team_id = team['team_id']
            metrics = self.get_team_performance_metrics(team_id, days_back)
            
            if 'error' not in metrics:
                team_summary = {
                    'team_id': team_id,
                    'team_name': team['name'],
                    'user_role': team['user_role'],
                    'sessions': metrics['total_sessions'],
                    'leads_processed': metrics['total_leads_processed'],
                    'avg_score': metrics.get('daily_trends', {}).get('avg_score', [0])[-1] if metrics.get('daily_trends') else 0,
                    'success_rate': metrics['avg_success_rate'],
                    'high_priority_leads': metrics['total_high_priority']
                }
                
                comparison['teams'].append(team_summary)
                comparison['summary']['total_sessions'] += team_summary['sessions']
                comparison['summary']['total_leads'] += team_summary['leads_processed']
                
                # Track best performing team
                if team_summary['avg_score'] > best_score:
                    best_score = team_summary['avg_score']
                    comparison['summary']['best_performing_team'] = team['name']
                
                # Track most active team
                if team_summary['sessions'] > most_sessions:
                    most_sessions = team_summary['sessions']
                    comparison['summary']['most_active_team'] = team['name']
        
        return comparison
    
    def check_team_data_access(self, user_id: str, team_id: str, required_role: TeamRole = TeamRole.MEMBER) -> bool:
        """Check if user can access team's analytics data"""
        return self.user_manager.check_team_permission(user_id, team_id, required_role)
    
    def get_user_accessible_teams(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all teams user can access for analytics"""
        return self.user_manager.get_user_teams(user_id)
    
    def generate_team_performance_report(self, team_id: str, days_back: int = 30) -> Dict[str, Any]:
        """Generate comprehensive team performance report"""
        metrics = self.get_team_performance_metrics(team_id, days_back)
        insights = self.get_team_lead_insights(team_id, days_back)
        
        if 'error' in metrics or 'error' in insights:
            return {"error": "Insufficient data for report generation"}
        
        # Get team info
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.execute("""
            SELECT t.name, t.description, u.first_name, u.last_name, COUNT(tm.user_id) as member_count
            FROM teams t
            LEFT JOIN users u ON t.owner_id = u.user_id
            LEFT JOIN team_memberships tm ON t.team_id = tm.team_id AND tm.is_active = TRUE
            WHERE t.team_id = ?
            GROUP BY t.team_id
        """, (team_id,))
        
        team_info = cursor.fetchone()
        conn.close()
        
        report = {
            'report_generated': datetime.now().isoformat(),
            'period_days': days_back,
            'team_info': {
                'name': team_info[0] if team_info else 'Unknown Team',
                'description': team_info[1] if team_info else '',
                'owner': f"{team_info[2]} {team_info[3]}" if team_info and team_info[2] else 'Unknown',
                'member_count': team_info[4] if team_info else 0
            },
            'executive_summary': {
                'total_sessions': metrics['total_sessions'],
                'total_leads': metrics['total_leads_processed'],
                'success_rate': f"{metrics['avg_success_rate']*100:.1f}%",
                'high_priority_leads': metrics['total_high_priority'],
                'avg_processing_time': f"{metrics['avg_processing_time']:.1f}s",
                'team_size': len(metrics.get('user_performance', {}))
            },
            'team_performance': metrics,
            'lead_insights': insights,
            'recommendations': self._generate_team_recommendations(metrics, insights)
        }
        
        return report
    
    def _generate_team_recommendations(self, metrics: Dict, insights: Dict) -> List[str]:
        """Generate team-specific recommendations"""
        recommendations = []
        
        # Team collaboration recommendations
        team_size = len(metrics.get('user_performance', {}))
        if team_size == 1:
            recommendations.append("🤝 Consider inviting team members to collaborate and share workload")
        elif team_size > 5:
            recommendations.append("👥 Large team detected - consider creating specialized sub-teams")
        
        # Performance distribution recommendations
        if 'user_performance' in metrics and len(metrics['user_performance']) > 1:
            user_scores = [stats['avg_score'] for stats in metrics['user_performance'].values()]
            score_variance = max(user_scores) - min(user_scores)
            
            if score_variance > 20:
                recommendations.append("📊 High variance in team member performance - consider training or process standardization")
        
        # Success rate recommendations
        if metrics['avg_success_rate'] < 0.9:
            recommendations.append("🔧 Team success rate below 90% - review API configurations and error handling")
        
        # Lead quality recommendations
        if insights['score_distribution']['high'] < insights['score_distribution']['low']:
            recommendations.append("🎯 Team finding more low-quality leads - consider refining targeting criteria")
        
        # Model performance recommendations
        if 'model_performance' in metrics and len(metrics['model_performance']) > 1:
            best_model = max(metrics['model_performance'].items(), 
                           key=lambda x: x[1]['avg_score'])[0]
            recommendations.append(f"🤖 Team's best performing model is {best_model} - consider standardizing")
        
        return recommendations
