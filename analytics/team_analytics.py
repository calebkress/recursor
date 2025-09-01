#!/usr/bin/env python3
"""
Team Analytics Engine for Recursor
Advanced analytics, performance tracking, and reporting for team collaboration
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import sqlite3
from collections import defaultdict
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

@dataclass
class ProcessingSession:
    """Represents a processing session for analytics"""
    session_id: str
    user: str
    timestamp: datetime
    input_file: str
    total_leads: int
    processed_leads: int
    success_rate: float
    avg_score: float
    high_priority_count: int
    processing_time: float
    model_used: str
    template_used: str
    clustering_enabled: bool
    clusters_created: int
    
    def to_dict(self):
        return asdict(self)

@dataclass
class LeadAnalytics:
    """Analytics data for individual leads"""
    company: str
    domain: str
    score: int
    priority: str
    industry_fit: float
    scale_indicators: float
    platform_maturity: float
    growth_churn_challenges: float
    revenue_sophistication: float
    processing_time: float
    session_id: str
    timestamp: datetime
    cluster_id: Optional[str] = None
    cluster_label: Optional[str] = None

class TeamAnalyticsDB:
    """SQLite database for team analytics storage"""
    
    def __init__(self, db_path: str = "analytics/team_analytics.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        
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
        
        conn.close()
    
    def save_session(self, session: ProcessingSession):
        """Save processing session to database"""
        conn = sqlite3.connect(self.db_path)
        
        conn.execute("""
            INSERT OR REPLACE INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.session_id, session.user, session.timestamp, session.input_file,
            session.total_leads, session.processed_leads, session.success_rate,
            session.avg_score, session.high_priority_count, session.processing_time,
            session.model_used, session.template_used, session.clustering_enabled,
            session.clusters_created
        ))
        
        conn.commit()
        conn.close()
    
    def save_leads(self, leads: List[LeadAnalytics]):
        """Save lead analytics to database"""
        conn = sqlite3.connect(self.db_path)
        
        for lead in leads:
            conn.execute("""
                INSERT INTO leads (
                    company, domain, score, priority, industry_fit, scale_indicators,
                    platform_maturity, growth_churn_challenges, revenue_sophistication,
                    processing_time, session_id, timestamp, cluster_id, cluster_label
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lead.company, lead.domain, lead.score, lead.priority,
                lead.industry_fit, lead.scale_indicators, lead.platform_maturity,
                lead.growth_churn_challenges, lead.revenue_sophistication,
                lead.processing_time, lead.session_id, lead.timestamp,
                lead.cluster_id, lead.cluster_label
            ))
        
        conn.commit()
        conn.close()
    
    def get_sessions(self, days_back: int = 30) -> pd.DataFrame:
        """Get sessions from last N days"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT * FROM sessions 
            WHERE timestamp >= datetime('now', '-{} days')
            ORDER BY timestamp DESC
        """.format(days_back)
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
        
        return df
    
    def get_leads(self, days_back: int = 30) -> pd.DataFrame:
        """Get leads from last N days"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT * FROM leads 
            WHERE timestamp >= datetime('now', '-{} days')
            ORDER BY timestamp DESC
        """.format(days_back)
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
        
        return df


class TeamAnalyticsEngine:
    """Main analytics engine for team insights"""
    
    def __init__(self, db_path: str = "analytics/team_analytics.db"):
        self.db = TeamAnalyticsDB(db_path)
    
    def record_processing_session(
        self, 
        results: List[Dict[str, Any]], 
        user: str = "system",
        input_file: str = "unknown",
        processing_time: float = 0.0,
        model_used: str = "gpt-4-turbo",
        template_used: str = "recurly_template.txt",
        clusters: Optional[Dict] = None
    ) -> str:
        """Record a processing session and return session ID"""
        
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user}"
        timestamp = datetime.now()
        
        # Calculate session metrics
        total_leads = len(results)
        processed_leads = sum(1 for r in results if 'score' in r and r.get('score', 0) > 0)
        success_rate = processed_leads / total_leads if total_leads > 0 else 0
        avg_score = np.mean([r.get('score', 0) for r in results if 'score' in r])
        high_priority_count = sum(1 for r in results if r.get('priority') == 'High')
        
        # Clustering metrics
        clustering_enabled = clusters is not None
        clusters_created = len(clusters) if clusters else 0
        
        # Create session record
        session = ProcessingSession(
            session_id=session_id,
            user=user,
            timestamp=timestamp,
            input_file=input_file,
            total_leads=total_leads,
            processed_leads=processed_leads,
            success_rate=success_rate,
            avg_score=avg_score,
            high_priority_count=high_priority_count,
            processing_time=processing_time,
            model_used=model_used,
            template_used=template_used,
            clustering_enabled=clustering_enabled,
            clusters_created=clusters_created
        )
        
        # Save session
        self.db.save_session(session)
        
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
        
        self.db.save_leads(lead_analytics)
        return session_id
    
    def get_team_performance_metrics(self, days_back: int = 30) -> Dict[str, Any]:
        """Get comprehensive team performance metrics"""
        sessions_df = self.db.get_sessions(days_back)
        leads_df = self.db.get_leads(days_back)
        
        if sessions_df.empty:
            return {"error": "No data available for the specified period"}
        
        metrics = {}
        
        # Overall metrics
        metrics['total_sessions'] = len(sessions_df)
        metrics['total_leads_processed'] = sessions_df['processed_leads'].sum()
        metrics['avg_success_rate'] = sessions_df['success_rate'].mean()
        metrics['avg_processing_time'] = sessions_df['processing_time'].mean()
        metrics['total_high_priority'] = sessions_df['high_priority_count'].sum()
        
        # User metrics
        user_metrics = sessions_df.groupby('user').agg({
            'session_id': 'count',
            'processed_leads': 'sum',
            'success_rate': 'mean',
            'avg_score': 'mean',
            'high_priority_count': 'sum'
        }).to_dict('index')
        metrics['user_performance'] = user_metrics
        
        # Model performance
        model_metrics = sessions_df.groupby('model_used').agg({
            'avg_score': 'mean',
            'success_rate': 'mean',
            'processing_time': 'mean',
            'session_id': 'count'
        }).to_dict('index')
        metrics['model_performance'] = model_metrics
        
        # Template performance
        template_metrics = sessions_df.groupby('template_used').agg({
            'avg_score': 'mean',
            'success_rate': 'mean',
            'session_id': 'count'
        }).to_dict('index')
        metrics['template_performance'] = template_metrics
        
        # Time-based trends
        sessions_df['date'] = sessions_df['timestamp'].dt.date
        daily_metrics = sessions_df.groupby('date').agg({
            'processed_leads': 'sum',
            'avg_score': 'mean',
            'success_rate': 'mean',
            'high_priority_count': 'sum'
        }).to_dict('list')
        metrics['daily_trends'] = daily_metrics
        
        return metrics
    
    def get_lead_scoring_insights(self, days_back: int = 30) -> Dict[str, Any]:
        """Get insights into lead scoring patterns"""
        leads_df = self.db.get_leads(days_back)
        
        if leads_df.empty:
            return {"error": "No lead data available"}
        
        insights = {}
        
        # Score distribution
        insights['score_distribution'] = {
            'high': len(leads_df[leads_df['score'] >= 75]),
            'medium': len(leads_df[(leads_df['score'] >= 50) & (leads_df['score'] < 75)]),
            'low': len(leads_df[leads_df['score'] < 50])
        }
        
        # Priority distribution
        insights['priority_distribution'] = leads_df['priority'].value_counts().to_dict()
        
        # Dimension analysis
        dimension_cols = ['industry_fit', 'scale_indicators', 'platform_maturity', 
                         'growth_churn_challenges', 'revenue_sophistication']
        
        dimension_stats = {}
        for dim in dimension_cols:
            dimension_stats[dim] = {
                'mean': leads_df[dim].mean(),
                'std': leads_df[dim].std(),
                'correlation_with_score': leads_df[dim].corr(leads_df['score'])
            }
        insights['dimension_analysis'] = dimension_stats
        
        # Top performing companies
        top_companies = leads_df.nlargest(10, 'score')[['company', 'score', 'priority']].to_dict('records')
        insights['top_companies'] = top_companies
        
        # Cluster analysis (if available)
        if 'cluster_label' in leads_df.columns and not leads_df['cluster_label'].isna().all():
            cluster_analysis = leads_df.groupby('cluster_label').agg({
                'score': ['count', 'mean', 'std'],
                'company': lambda x: list(x)[:5]  # Top 5 companies per cluster
            }).to_dict()
            insights['cluster_analysis'] = cluster_analysis
        
        return insights
    
    def generate_performance_report(self, days_back: int = 30) -> Dict[str, Any]:
        """Generate comprehensive team performance report"""
        metrics = self.get_team_performance_metrics(days_back)
        insights = self.get_lead_scoring_insights(days_back)
        
        if 'error' in metrics or 'error' in insights:
            return {"error": "Insufficient data for report generation"}
        
        report = {
            'report_generated': datetime.now().isoformat(),
            'period_days': days_back,
            'executive_summary': {
                'total_sessions': metrics['total_sessions'],
                'total_leads': metrics['total_leads_processed'],
                'success_rate': f"{metrics['avg_success_rate']*100:.1f}%",
                'high_priority_leads': metrics['total_high_priority'],
                'avg_processing_time': f"{metrics['avg_processing_time']:.1f}s"
            },
            'team_performance': metrics,
            'lead_insights': insights,
            'recommendations': self._generate_recommendations(metrics, insights)
        }
        
        return report
    
    def _generate_recommendations(self, metrics: Dict, insights: Dict) -> List[str]:
        """Generate actionable recommendations based on analytics"""
        recommendations = []
        
        # Success rate recommendations
        if metrics['avg_success_rate'] < 0.9:
            recommendations.append("🔧 Consider optimizing API error handling - success rate is below 90%")
        
        # Model performance recommendations
        if 'model_performance' in metrics:
            best_model = max(metrics['model_performance'].items(), 
                           key=lambda x: x[1]['avg_score'])[0]
            recommendations.append(f"🤖 Best performing model is {best_model} - consider standardizing")
        
        # Template recommendations
        if 'template_performance' in metrics:
            best_template = max(metrics['template_performance'].items(),
                              key=lambda x: x[1]['avg_score'])[0]
            if metrics['template_performance'][best_template]['session_id'] > 1:
                recommendations.append(f"📝 Template '{best_template}' shows best results")
        
        # Lead quality recommendations
        if insights['score_distribution']['high'] < insights['score_distribution']['low']:
            recommendations.append("📊 Most leads are low-scoring - consider refining targeting criteria")
        
        # Dimension recommendations
        if 'dimension_analysis' in insights:
            best_dimension = max(insights['dimension_analysis'].items(),
                               key=lambda x: x[1]['correlation_with_score'])[0]
            recommendations.append(f"🎯 '{best_dimension}' shows strongest correlation with scores")
        
        return recommendations
    
    def create_performance_charts(self, days_back: int = 30) -> Dict[str, go.Figure]:
        """Create performance visualization charts"""
        metrics = self.get_team_performance_metrics(days_back)
        insights = self.get_lead_scoring_insights(days_back)
        
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
        
        # 2. User performance chart
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
                title="User Performance Comparison",
                yaxis=dict(title="Number of Sessions", side="left"),
                yaxis2=dict(title="Average Score", side="right", overlaying="y"),
                hovermode="x"
            )
            charts['user_performance'] = fig
        
        # 3. Score distribution chart
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
            fig.update_layout(title="Lead Score Distribution")
            charts['score_distribution'] = fig
        
        # 4. Dimension correlation heatmap
        if 'dimension_analysis' in insights:
            dimensions = list(insights['dimension_analysis'].keys())
            correlations = [insights['dimension_analysis'][d]['correlation_with_score'] 
                          for d in dimensions]
            
            # Create color scale based on correlation values
            colors = ['#d73027' if c < 0 else '#1a9850' if c > 0.5 else '#fee08b' 
                     for c in correlations]
            
            fig = go.Figure(data=go.Bar(
                x=[d.replace('_', ' ').title() for d in dimensions],
                y=correlations,
                marker_color=colors
            ))
            fig.update_layout(
                title="Dimension Correlation with Lead Score",
                xaxis_title="Scoring Dimensions",
                yaxis_title="Correlation with Final Score"
            )
            charts['dimension_correlation'] = fig
        
        return charts


# Utility functions for dashboard integration
def load_and_record_session(
    results_file: str,
    user: str = "dashboard_user",
    analytics_engine: Optional[TeamAnalyticsEngine] = None
) -> str:
    """Load results from file and record analytics session"""
    
    if analytics_engine is None:
        analytics_engine = TeamAnalyticsEngine()
    
    try:
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        session_id = analytics_engine.record_processing_session(
            results=results,
            user=user,
            input_file=Path(results_file).name,
            processing_time=0.0  # Would need to be tracked separately
        )
        
        return session_id
        
    except Exception as e:
        print(f"Error loading results: {e}")
        return ""


if __name__ == "__main__":
    # Demo usage
    engine = TeamAnalyticsEngine()
    
    # Generate some test data
    test_results = [
        {
            "company": "TestCorp1",
            "domain": "test1.com", 
            "score": 85,
            "priority": "High",
            "breakdown": {
                "industry_fit": 18,
                "scale_indicators": 16,
                "platform_maturity": 17,
                "growth_churn_challenges": 15,
                "revenue_sophistication": 19
            }
        },
        {
            "company": "TestCorp2", 
            "domain": "test2.com",
            "score": 65,
            "priority": "Medium",
            "breakdown": {
                "industry_fit": 12,
                "scale_indicators": 14,
                "platform_maturity": 13,
                "growth_churn_challenges": 12,
                "revenue_sophistication": 14
            }
        }
    ]
    
    session_id = engine.record_processing_session(
        results=test_results,
        user="test_user",
        input_file="test_leads.csv"
    )
    
    print(f"Recorded session: {session_id}")
    
    # Get performance report
    report = engine.generate_performance_report(days_back=30)
    print("\nPerformance Report:")
    print(json.dumps(report['executive_summary'], indent=2))
