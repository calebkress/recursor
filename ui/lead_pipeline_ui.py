#!/usr/bin/env python3
"""
Lead Pipeline UI Components
Personal and team lead management interface with multi-tenant data access
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

from data.lead_intelligence import LeadIntelligenceEngine, DataAccessController, LeadStatus
from auth.user_manager import UserManager

def init_intelligence_state():
    """Initialize lead intelligence system in session state"""
    if 'lead_intelligence' not in st.session_state:
        st.session_state.lead_intelligence = LeadIntelligenceEngine()
    
    if 'data_access_controller' not in st.session_state:
        st.session_state.data_access_controller = DataAccessController(
            st.session_state.user_manager,
            st.session_state.lead_intelligence
        )

def show_personal_pipeline():
    """Display user's personal lead pipeline"""
    init_intelligence_state()
    
    current_user = st.session_state.user
    intelligence = st.session_state.lead_intelligence
    
    # Back to dashboard button
    if st.button("← Back to Dashboard", key="back_to_dashboard_personal"):
        st.session_state.show_personal_pipeline = False
        st.rerun()
    
    st.title(f"📊 {current_user.first_name}'s Lead Pipeline")
    st.markdown("Your personal lead database and scoring history")
    
    # Pipeline overview metrics
    performance = intelligence.get_user_performance_summary(current_user.user_id)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Companies", performance['total_in_pipeline'])
    
    with col2:
        st.metric("Conversion Rate", f"{performance['conversion_rate']*100:.1f}%")
    
    with col3:
        session_metrics = performance['session_metrics']
        avg_score = session_metrics.get('avg_score', 0) or 0
        st.metric("Avg Score", f"{avg_score:.1f}")
    
    with col4:
        high_priority = session_metrics.get('high_priority_total', 0) or 0
        st.metric("High Priority Leads", high_priority)
    
    # Status filter
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Filter by Status:",
            ["All"] + [status.value.title() for status in LeadStatus],
            key="personal_status_filter"
        )
    
    with col2:
        sort_by = st.selectbox(
            "Sort by:",
            ["Score (High to Low)", "Last Updated", "Company Name"],
            key="personal_sort"
        )
    
    with col3:
        if st.button("🔄 Refresh Pipeline"):
            st.cache_data.clear()
            st.rerun()
    
    # Get pipeline data
    filter_status = None if status_filter == "All" else LeadStatus(status_filter.lower().replace(" ", "_"))
    pipeline = intelligence.get_user_pipeline(current_user.user_id, status_filter=filter_status)
    
    if not pipeline:
        st.info("🎯 No leads in your pipeline yet. Start scoring some companies to build your personal dataset!")
        if st.button("➕ Score New Companies"):
            st.session_state.show_personal_pipeline = False
            st.rerun()
        return
    
    # Display pipeline
    st.header("📋 Your Lead Pipeline")
    
    for lead in pipeline:
        with st.expander(f"{lead['name']} - Score: {lead['current_score']}/100"):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown(f"**Current Score:** {lead['current_score']}/100")
                st.markdown(f"**Status:** {lead['status'].title()}")
                st.markdown(f"**Last Updated:** {lead['last_updated'][:10]}")
                
                if lead.get('conversion_probability'):
                    st.markdown(f"**Conversion Probability:** {lead['conversion_probability']*100:.1f}%")
                
                # Status update
                new_status = st.selectbox(
                    "Update Status:",
                    [status.value.title() for status in LeadStatus],
                    index=[status.value for status in LeadStatus].index(lead['status']),
                    key=f"status_{lead['name']}"
                )
                
                if st.button(f"Update {lead['name']}", key=f"update_{lead['name']}"):
                    success = intelligence.update_lead_status(
                        current_user.user_id,
                        lead['name'],
                        LeadStatus(new_status.lower().replace(" ", "_"))
                    )
                    if success:
                        st.success("Status updated!")
                        st.rerun()
            
            with col2:
                st.markdown(f"**Domain:** {lead.get('domain', 'Unknown')}")
                st.markdown(f"**Industry:** {lead.get('industry', 'Unknown')}")
                
                if lead['personal_notes']:
                    st.markdown(f"**Your Notes:** {lead['personal_notes']}")
                
                if lead.get('next_action'):
                    st.markdown(f"**Next Action:** {lead['next_action']}")
                
                # Add notes
                new_notes = st.text_area(
                    "Personal Notes:",
                    value=lead['personal_notes'],
                    key=f"notes_{lead['name']}",
                    height=60
                )
                
                if new_notes != lead['personal_notes']:
                    if st.button(f"Save Notes", key=f"save_notes_{lead['name']}"):
                        # TODO: Implement note saving
                        st.info("Note saving coming soon!")

def show_team_intelligence():
    """Display team-level lead intelligence (for team leads and managers)"""
    init_intelligence_state()
    
    # Back to dashboard button
    if st.button("← Back to Dashboard", key="back_to_dashboard_team"):
        st.session_state.show_team_intelligence = False
        st.rerun()
    
    current_user = st.session_state.user
    user_manager = st.session_state.user_manager
    intelligence = st.session_state.lead_intelligence
    data_controller = st.session_state.data_access_controller
    
    # Get user's teams where they have leadership access
    user_teams = user_manager.get_user_teams(current_user.user_id)
    leadership_teams = [
        team for team in user_teams 
        if team['user_role'] in ['owner', 'admin'] or current_user.role.value in ['manager']
    ]
    
    if not leadership_teams:
        st.warning("🔒 You don't have access to any team intelligence data.")
        st.info("Team leads, managers, and admins can view team-level lead intelligence.")
        return
    
    st.title("🏢 Team Lead Intelligence")
    st.markdown("Team-wide lead patterns, performance, and collective insights")
    
    # Team selection
    if len(leadership_teams) > 1:
        selected_team = st.selectbox(
            "Select Team:",
            options=[team['name'] for team in leadership_teams],
            key="team_intelligence_selector"
        )
        team_id = next(team['team_id'] for team in leadership_teams if team['name'] == selected_team)
    else:
        selected_team = leadership_teams[0]['name']
        team_id = leadership_teams[0]['team_id']
        st.info(f"Showing data for: **{selected_team}**")
    
    # Get permissions for team data access
    permissions = data_controller.get_user_permissions(current_user.user_id, current_user.user_id)
    
    # Team-wide company data
    team_companies = intelligence.db.get_team_companies(team_id, current_user.user_id, permissions)
    
    if not team_companies:
        st.info("📋 No team lead data available yet.")
        st.markdown("Team members need to start scoring companies to build team intelligence.")
        return
    
    # Team metrics overview
    st.header("📊 Team Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Unique Companies", len(team_companies))
    
    with col2:
        avg_team_score = sum(company['avg_score'] for company in team_companies) / len(team_companies)
        st.metric("Avg Team Score", f"{avg_team_score:.1f}")
    
    with col3:
        total_users_scoring = sum(company['users_scored'] for company in team_companies)
        st.metric("Total Scoring Activity", total_users_scoring)
    
    with col4:
        high_score_companies = len([c for c in team_companies if c['avg_score'] >= 75])
        st.metric("High-Score Companies", high_score_companies)
    
    # Team company list
    st.header("🎯 Team Companies")
    
    # Convert to dataframe for easy display
    team_df = pd.DataFrame(team_companies)
    team_df['avg_score'] = team_df['avg_score'].round(1)
    
    # Display as interactive table
    st.dataframe(
        team_df[['name', 'domain', 'industry', 'avg_score', 'users_scored', 'last_activity']],
        use_container_width=True,
        column_config={
            'name': 'Company',
            'domain': 'Domain', 
            'industry': 'Industry',
            'avg_score': st.column_config.NumberColumn('Avg Score', format="%.1f"),
            'users_scored': st.column_config.NumberColumn('Team Members Scored'),
            'last_activity': 'Last Activity'
        }
    )
    
    # Team member performance
    st.header("👥 Team Member Performance")
    
    # Get all team members
    team_members = user_manager.get_team_members(team_id)
    
    member_performance = []
    for member in team_members:
        perf = intelligence.get_user_performance_summary(member['user_id'])
        session_metrics = perf['session_metrics']
        avg_score = session_metrics.get('avg_score', 0) or 0
        total_sessions = session_metrics.get('total_sessions', 0) or 0
        
        member_performance.append({
            'Name': f"{member['first_name']} {member['last_name']}",
            'Companies in Pipeline': perf['total_in_pipeline'],
            'Conversion Rate': f"{perf['conversion_rate']*100:.1f}%",
            'Avg Score': f"{avg_score:.1f}",
            'Total Sessions': total_sessions
        })
    
    member_df = pd.DataFrame(member_performance)
    st.dataframe(member_df, use_container_width=True)

def show_lead_status_board():
    """Kanban-style view of leads by status"""
    init_intelligence_state()
    
    # Back to dashboard button
    if st.button("← Back to Dashboard", key="back_to_dashboard_status"):
        st.session_state.show_status_board = False
        st.rerun()
    
    current_user = st.session_state.user
    intelligence = st.session_state.lead_intelligence
    
    st.title("📋 Lead Status Board")
    st.markdown("Kanban-style view of your leads by pipeline stage")
    
    # Get all user's leads
    all_leads = intelligence.get_user_pipeline(current_user.user_id, limit=500)
    
    if not all_leads:
        st.info("No leads in your pipeline yet.")
        return
    
    # Group by status
    leads_by_status = {}
    for lead in all_leads:
        status = lead['status']
        if status not in leads_by_status:
            leads_by_status[status] = []
        leads_by_status[status].append(lead)
    
    # Create columns for each status
    status_columns = [
        ('prospect', '🎯 Prospects'),
        ('contacted', '📧 Contacted'), 
        ('replied', '💬 Replied'),
        ('demo', '🎥 Demo'),
        ('closed-won', '✅ Won'),
        ('closed-lost', '❌ Lost')
    ]
    
    # Show status columns
    cols = st.columns(len(status_columns))
    
    for i, (status_key, status_display) in enumerate(status_columns):
        with cols[i]:
            st.subheader(status_display)
            status_leads = leads_by_status.get(status_key, [])
            st.caption(f"{len(status_leads)} companies")
            
            for lead in status_leads[:5]:  # Show top 5 per column
                with st.container():
                    st.markdown(f"**{lead['name']}**")
                    st.markdown(f"Score: {lead['current_score']}")
                    st.markdown(f"Updated: {lead['last_updated'][:10]}")
                    st.markdown("---")
            
            if len(status_leads) > 5:
                st.caption(f"... and {len(status_leads) - 5} more")

def integrate_with_dashboard():
    """Integration functions to add to main dashboard"""
    
    # Add to sidebar navigation
    def add_pipeline_navigation():
        with st.sidebar:
            st.markdown("### 🎯 Lead Intelligence")
            
            if st.button("📊 My Pipeline"):
                st.session_state.show_personal_pipeline = True
                st.rerun()
            
            if st.button("📋 Status Board"):
                st.session_state.show_status_board = True
                st.rerun()
            
            # Show team intelligence option for leaders
            user = st.session_state.user
            user_teams = st.session_state.user_manager.get_user_teams(user.user_id)
            
            has_leadership = any(
                team['user_role'] in ['owner', 'admin'] 
                for team in user_teams
            ) or user.role.value in ['manager']
            
            if has_leadership:
                if st.button("🏢 Team Intelligence"):
                    st.session_state.show_team_intelligence = True
                    st.rerun()
    
    # Handle navigation routing
    def handle_pipeline_navigation():
        """Handle navigation for pipeline views"""
        if st.session_state.get('show_personal_pipeline', False):
            show_personal_pipeline()
            return True
        
        if st.session_state.get('show_status_board', False):
            show_lead_status_board()
            return True
        
        if st.session_state.get('show_team_intelligence', False):
            show_team_intelligence()
            return True
        
        return False
    
    return add_pipeline_navigation, handle_pipeline_navigation

def enhance_live_processing_with_intelligence():
    """Enhance the live processing to integrate with personal datasets"""
    
    def record_live_session(scored_results: List[Dict], user_id: str, team_id: str, model_used: str):
        """Record live processing session in user's dataset"""
        init_intelligence_state()
        
        intelligence = st.session_state.lead_intelligence
        
        session_id = intelligence.record_scoring_session(
            user_id=user_id,
            team_id=team_id,
            scored_results=scored_results,
            session_type="live_processing",
            model_used=model_used
        )
        
        return session_id
    
    return record_live_session

# Example usage functions
def demo_personal_intelligence():
    """Demo function to populate personal intelligence data"""
    init_intelligence_state()
    
    if not st.session_state.user:
        return
    
    st.header("🎲 Demo: Populate Personal Intelligence")
    
    if st.button("Generate Demo Personal Dataset"):
        intelligence = st.session_state.lead_intelligence
        current_user = st.session_state.user
        
        # Get user's team
        user_teams = st.session_state.user_manager.get_user_teams(current_user.user_id)
        team_id = user_teams[0]['team_id'] if user_teams else "demo-team"
        
        # Demo scored results with variety of statuses
        demo_results = [
            {
                "company": "Calendly",
                "domain": "calendly.com",
                "score": 89,
                "priority": "High",
                "industry": "SaaS",
                "breakdown": {"industry_fit": 19, "scale_indicators": 18, "platform_maturity": 17, "growth_churn_challenges": 18, "revenue_sophistication": 17}
            },
            {
                "company": "Typeform", 
                "domain": "typeform.com",
                "score": 76,
                "priority": "High",
                "industry": "SaaS",
                "breakdown": {"industry_fit": 16, "scale_indicators": 15, "platform_maturity": 15, "growth_churn_challenges": 15, "revenue_sophistication": 15}
            },
            {
                "company": "Figma",
                "domain": "figma.com", 
                "score": 82,
                "priority": "High",
                "industry": "SaaS",
                "breakdown": {"industry_fit": 17, "scale_indicators": 16, "platform_maturity": 17, "growth_churn_challenges": 16, "revenue_sophistication": 16}
            }
        ]
        
        session_id = intelligence.record_scoring_session(
            user_id=current_user.user_id,
            team_id=team_id,
            scored_results=demo_results,
            session_type="demo",
            model_used="gpt-4o"
        )
        
        # Update some leads to different statuses
        intelligence.update_lead_status(current_user.user_id, "Calendly", LeadStatus.CONTACTED, "Sent initial outreach email")
        intelligence.update_lead_status(current_user.user_id, "Typeform", LeadStatus.REPLIED, "Responded positively, scheduling demo")
        
        st.success(f"✅ Demo dataset created! Session ID: {session_id[:8]}...")
        st.info("🔄 Refresh your pipeline to see the new data")

if __name__ == "__main__":
    # This would be integrated into the main dashboard
    st.set_page_config(page_title="Lead Pipeline Demo", layout="wide")
    
    # Demo the pipeline UI
    st.title("🎯 Lead Pipeline Demo")
    demo_personal_intelligence()
