#!/usr/bin/env python3
"""
Recursor Dashboard - Interactive lead scoring visualization

Run with: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import io
from typing import Dict, List, Any

# Import our modules for live processing
from enrich.serp_api import LeadEnricher
from score.scorer import LeadScorer
from analysis.lead_clustering import LeadClusterer
from analytics.team_analytics import TeamAnalyticsEngine
from analytics.multi_tenant_analytics import MultiTenantAnalyticsEngine
from auth.auth_ui import require_authentication, handle_authenticated_navigation
from auth.user_manager import get_current_user

# Page configuration
st.set_page_config(
    page_title="Recursor - Lead Scoring Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
.metric-card {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    border: 1px solid #e0e0e0;
}
.high-priority {
    background-color: #d4edda;
    color: #155724;
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    font-weight: bold;
}
.medium-priority {
    background-color: #fff3cd;
    color: #856404;
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    font-weight: bold;
}
.low-priority {
    background-color: #f8d7da;
    color: #721c24;
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

def load_scored_data(uploaded_file) -> List[Dict]:
    """Load scored data from uploaded JSON file"""
    try:
        content = uploaded_file.read()
        data = json.loads(content)
        return data
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return []

def create_score_distribution_chart(df: pd.DataFrame):
    """Create score distribution histogram"""
    fig = px.histogram(
        df, 
        x='score', 
        nbins=20,
        title="Lead Score Distribution",
        labels={'score': 'Lead Score', 'count': 'Number of Companies'},
        color_discrete_sequence=['#1f77b4']
    )
    fig.update_layout(
        xaxis=dict(range=[0, 100]),
        showlegend=False
    )
    return fig

def create_priority_breakdown_chart(df: pd.DataFrame):
    """Create priority breakdown pie chart"""
    priority_counts = df['priority'].value_counts()
    colors = {'High': '#28a745', 'Medium': '#ffc107', 'Low': '#dc3545'}
    
    fig = go.Figure(data=[go.Pie(
        labels=priority_counts.index,
        values=priority_counts.values,
        marker_colors=[colors.get(p, '#6c757d') for p in priority_counts.index]
    )])
    
    fig.update_layout(
        title="Priority Distribution",
        showlegend=True
    )
    return fig

def create_scoring_dimensions_chart(df: pd.DataFrame):
    """Create radar chart for average scoring dimensions"""
    # Extract breakdown data
    breakdown_cols = ['industry_fit', 'scale_indicators', 'platform_maturity', 
                     'growth_churn_challenges', 'revenue_sophistication']
    
    # Calculate averages for each dimension
    avg_scores = {}
    for col in breakdown_cols:
        scores = []
        for _, row in df.iterrows():
            if 'breakdown' in row and col in row['breakdown']:
                scores.append(row['breakdown'][col])
        if scores:
            avg_scores[col.replace('_', ' ').title()] = sum(scores) / len(scores)
    
    if avg_scores:
        categories = list(avg_scores.keys())
        values = list(avg_scores.values())
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='Average Scores'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 20]
                )
            ),
            title="Average Scoring Dimensions",
            showlegend=True
        )
        return fig
    return None

def create_company_comparison_chart(df: pd.DataFrame):
    """Create horizontal bar chart comparing companies"""
    # Sort by score descending
    df_sorted = df.sort_values('score', ascending=True)
    
    # Color by priority
    color_map = {'High': '#28a745', 'Medium': '#ffc107', 'Low': '#dc3545'}
    colors = [color_map.get(p, '#6c757d') for p in df_sorted['priority']]
    
    fig = go.Figure(data=[go.Bar(
        x=df_sorted['score'],
        y=df_sorted['company'],
        orientation='h',
        marker_color=colors,
        text=df_sorted['score'],
        textposition='inside'
    )])
    
    fig.update_layout(
        title="Company Scores Comparison",
        xaxis_title="Score",
        yaxis_title="Company",
        height=max(400, len(df) * 30),
        showlegend=False
    )
    
    return fig

def format_priority(priority: str) -> str:
    """Format priority with colored styling"""
    if priority == 'High':
        return '<span class="high-priority">High</span>'
    elif priority == 'Medium':
        return '<span class="medium-priority">Medium</span>'
    else:
        return '<span class="low-priority">Low</span>'

def main():
    # Header
    st.title("🎯 Recursor Lead Scoring Dashboard")
    st.markdown("Interactive visualization for lead enrichment and scoring results")
    
    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        mode = st.radio(
            "Choose Mode:",
            ["Upload Results", "Live Processing", "Clustering Analysis", "Team Analytics"]
        )
    
    if mode == "Upload Results":
        st.header("Upload Scored Results")
        
        uploaded_file = st.file_uploader(
            "Upload scored JSON file", 
            type=['json'],
            help="Upload a JSON file generated by the Recursor CLI"
        )
        
        if uploaded_file is not None:
            data = load_scored_data(uploaded_file)
            
            if data:
                # Convert to DataFrame
                df = pd.json_normalize(data)
                
                # Ensure required columns exist
                required_cols = ['company', 'score', 'priority', 'justification']
                missing_cols = [col for col in required_cols if col not in df.columns]
                
                if missing_cols:
                    st.error(f"Missing required columns: {missing_cols}")
                    return
                
                # Overview metrics
                st.header("📊 Overview")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Companies", len(df))
                
                with col2:
                    avg_score = df['score'].mean()
                    st.metric("Average Score", f"{avg_score:.1f}")
                
                with col3:
                    high_priority = len(df[df['priority'] == 'High'])
                    st.metric("High Priority Leads", high_priority)
                
                with col4:
                    top_score = df['score'].max()
                    st.metric("Top Score", f"{top_score}")
                
                # Charts
                st.header("📈 Analytics")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_dist = create_score_distribution_chart(df)
                    st.plotly_chart(fig_dist, use_container_width=True)
                
                with col2:
                    fig_priority = create_priority_breakdown_chart(df)
                    st.plotly_chart(fig_priority, use_container_width=True)
                
                # Radar chart if breakdown data exists
                fig_radar = create_scoring_dimensions_chart(df)
                if fig_radar:
                    st.plotly_chart(fig_radar, use_container_width=True)
                
                # Company comparison
                fig_comparison = create_company_comparison_chart(df)
                st.plotly_chart(fig_comparison, use_container_width=True)
                
                # Detailed results table
                st.header("📋 Detailed Results")
                
                # Filters
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    priority_filter = st.selectbox(
                        "Filter by Priority",
                        ['All'] + list(df['priority'].unique())
                    )
                
                with col2:
                    min_score = st.slider(
                        "Minimum Score",
                        min_value=0,
                        max_value=100,
                        value=0
                    )
                
                with col3:
                    sort_by = st.selectbox(
                        "Sort by",
                        ['Score (High to Low)', 'Score (Low to High)', 'Company Name']
                    )
                
                # Apply filters
                filtered_df = df[df['score'] >= min_score]
                if priority_filter != 'All':
                    filtered_df = filtered_df[filtered_df['priority'] == priority_filter]
                
                # Apply sorting
                if sort_by == 'Score (High to Low)':
                    filtered_df = filtered_df.sort_values('score', ascending=False)
                elif sort_by == 'Score (Low to High)':
                    filtered_df = filtered_df.sort_values('score', ascending=True)
                else:
                    filtered_df = filtered_df.sort_values('company')
                
                # Display results
                for _, row in filtered_df.iterrows():
                    with st.expander(f"{row['company']} - Score: {row['score']}/100"):
                        col1, col2 = st.columns([1, 2])
                        
                        with col1:
                            st.markdown(f"**Priority:** {format_priority(row['priority'])}", unsafe_allow_html=True)
                            st.markdown(f"**Score:** {row['score']}/100")
                            
                            # Show breakdown if available
                            if 'breakdown' in row and isinstance(row['breakdown'], dict):
                                st.markdown("**Dimension Scores:**")
                                for dim, score in row['breakdown'].items():
                                    dim_name = dim.replace('_', ' ').title()
                                    st.markdown(f"- {dim_name}: {score}/20")
                        
                        with col2:
                            st.markdown(f"**Justification:** {row['justification']}")
                            
                            if 'summary' in row and row['summary']:
                                st.markdown("**Key Insights:**")
                                for insight in row['summary']:
                                    st.markdown(f"• {insight}")
                            
                            if 'next_steps' in row and row['next_steps']:
                                st.markdown(f"**Next Steps:** {row['next_steps']}")
    
    elif mode == "Live Processing":
        st.header("🚀 Live Processing")
        st.markdown("Process companies in real-time using the Recursor pipeline")
        
        # Input methods
        input_method = st.radio(
            "Input Method:",
            ["Manual Entry", "CSV Upload"]
        )
        
        companies = []
        
        if input_method == "Manual Entry":
            company_input = st.text_area(
                "Enter company names (one per line):",
                placeholder="Shopify\nZoom\nNetflix"
            )
            
            if company_input:
                companies = [c.strip() for c in company_input.split('\n') if c.strip()]
        
        else:  # CSV Upload
            uploaded_csv = st.file_uploader(
                "Upload CSV with company names",
                type=['csv'],
                help="CSV should have a 'company' column"
            )
            
            if uploaded_csv is not None:
                try:
                    df_input = pd.read_csv(uploaded_csv)
                    if 'company' in df_input.columns:
                        companies = df_input['company'].tolist()
                        st.success(f"Loaded {len(companies)} companies from CSV")
                    else:
                        st.error("CSV must have a 'company' column")
                except Exception as e:
                    st.error(f"Error reading CSV: {e}")
        
        if companies:
            st.write(f"**Companies to process:** {', '.join(companies)}")
            
            col1, col2 = st.columns(2)
            with col1:
                model_choice = st.selectbox(
                    "OpenAI Model:",
                    ['gpt-3.5-turbo', 'gpt-4o-mini', 'gpt-4o']
                )
            
            if st.button("🚀 Process Companies", type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                results = []
                
                # Initialize components
                enricher = LeadEnricher()
                scorer = LeadScorer(model=model_choice)
                
                total_steps = len(companies) * 2  # Enrich + Score
                current_step = 0
                
                for company in companies:
                    # Enrichment step
                    status_text.text(f"Enriching {company}...")
                    try:
                        enriched = enricher.enrich_company(company)
                    except Exception as e:
                        st.warning(f"Warning: Error enriching {company}: {e}")
                        enriched = {
                            "company": company,
                            "hiring_signals": [],
                            "tech_stack": [],
                            "news_mentions": []
                        }
                    
                    current_step += 1
                    progress_bar.progress(current_step / total_steps)
                    
                    # Scoring step
                    status_text.text(f"Scoring {company}...")
                    try:
                        scored = scorer.score_lead(enriched, template_name='recurly_template.txt')
                        results.append(scored)
                    except Exception as e:
                        st.warning(f"Warning: Error scoring {company}: {e}")
                        results.append({
                            "company": company,
                            "score": 0,
                            "error": str(e)
                        })
                    
                    current_step += 1
                    progress_bar.progress(current_step / total_steps)
                
                status_text.text("Processing complete!")
                progress_bar.progress(1.0)
                
                # Display results
                if results:
                    st.success(f"Processed {len(results)} companies successfully!")
                    
                    # Convert to DataFrame for display
                    df_results = pd.json_normalize(results)
                    
                    # Show quick summary
                    st.header("Quick Results")
                    df_summary = df_results[['company', 'score', 'priority']].sort_values('score', ascending=False)
                    st.dataframe(df_summary, use_container_width=True)
                    
                    # Download button
                    json_results = json.dumps(results, indent=2)
                    st.download_button(
                        label="Download Results as JSON",
                        data=json_results,
                        file_name="recursor_results.json",
                        mime="application/json"
                    )
        
        else:
            st.info("Enter company names or upload a CSV to get started")
    
    elif mode == "Clustering Analysis":
        st.header("🔍 Clustering Analysis")
        st.markdown("Analyze and cluster your scored leads to identify patterns and target segments")
        
        uploaded_file = st.file_uploader(
            "Upload scored JSON file for clustering", 
            type=['json'],
            help="Upload a JSON file with scored leads to perform clustering analysis"
        )
        
        if uploaded_file is not None:
            data = load_scored_data(uploaded_file)
            
            if data and len(data) >= 3:
                st.success(f"Loaded {len(data)} scored leads")
                
                # Clustering options
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    clustering_method = st.selectbox(
                        "Clustering Method:",
                        ['kmeans', 'hierarchical', 'dbscan'],
                        help="Choose clustering algorithm"
                    )
                
                with col2:
                    n_clusters = st.number_input(
                        "Number of Clusters (0 = auto-detect):",
                        min_value=0,
                        max_value=10,
                        value=0,
                        help="Leave as 0 to automatically determine optimal number"
                    )
                
                with col3:
                    random_seed = st.number_input(
                        "Random Seed:",
                        min_value=1,
                        value=42,
                        help="For reproducible results"
                    )
                
                if st.button("🔍 Perform Clustering", type="primary"):
                    with st.spinner("Performing clustering analysis..."):
                        try:
                            # Initialize clusterer
                            clusterer = LeadClusterer(random_state=random_seed)
                            
                            # Perform clustering
                            clusters = clusterer.cluster_leads(
                                data, 
                                method=clustering_method,
                                n_clusters=n_clusters if n_clusters > 0 else None
                            )
                            
                            if clusters:
                                st.success(f"Successfully created {len(clusters)} clusters!")
                                
                                # Cluster overview
                                st.header("📊 Cluster Overview")
                                
                                cluster_data = []
                                for cluster_id, cluster in clusters.items():
                                    cluster_data.append({
                                        'Cluster': f"Cluster {cluster_id}",
                                        'Label': cluster.cluster_label,
                                        'Size': cluster.size,
                                        'Avg Score': f"{cluster.avg_score:.1f}",
                                        'Companies': ', '.join(cluster.companies[:3]) + ('...' if len(cluster.companies) > 3 else '')
                                    })
                                
                                cluster_df = pd.DataFrame(cluster_data)
                                st.dataframe(cluster_df, use_container_width=True)
                                
                                # Cluster visualization
                                st.header("📈 Cluster Visualization")
                                
                                # Create cluster size chart
                                fig_sizes = px.bar(
                                    x=list(clusters.keys()),
                                    y=[cluster.size for cluster in clusters.values()],
                                    title="Cluster Sizes",
                                    labels={'x': 'Cluster ID', 'y': 'Number of Companies'}
                                )
                                st.plotly_chart(fig_sizes, use_container_width=True)
                                
                                # Create cluster score comparison
                                fig_scores = px.bar(
                                    x=[f"Cluster {cid}" for cid in clusters.keys()],
                                    y=[cluster.avg_score for cluster in clusters.values()],
                                    title="Average Cluster Scores",
                                    labels={'x': 'Cluster', 'y': 'Average Score'}
                                )
                                st.plotly_chart(fig_scores, use_container_width=True)
                                
                                # Detailed cluster insights
                                st.header("🎯 Detailed Cluster Insights")
                                
                                for cluster_id in sorted(clusters.keys()):
                                    cluster = clusters[cluster_id]
                                    insights = clusterer.get_cluster_insights(cluster_id)
                                    
                                    with st.expander(f"🔍 {cluster.cluster_label} (Score: {cluster.avg_score:.1f})"):
                                        col1, col2 = st.columns([1, 1])
                                        
                                        with col1:
                                            st.markdown(f"**Companies ({cluster.size}):**")
                                            for company in cluster.companies:
                                                st.markdown(f"• {company}")
                                            
                                            st.markdown(f"**Common Themes:**")
                                            for theme in insights['cluster_info']['common_themes'][:5]:
                                                st.markdown(f"• {theme}")
                                        
                                        with col2:
                                            st.markdown(f"**🎯 Recommendations:**")
                                            for i, rec in enumerate(insights['recommendations'], 1):
                                                st.markdown(f"{i}. {rec}")
                                            
                                            st.markdown(f"**📋 Next Steps:**")
                                            for i, step in enumerate(insights['next_steps'], 1):
                                                st.markdown(f"{i}. {step}")
                                
                                # Export clustering results
                                st.header("💾 Export Results")
                                
                                # Generate cluster export data
                                cluster_export = {}
                                for cluster_id, cluster in clusters.items():
                                    insights = clusterer.get_cluster_insights(cluster_id)
                                    cluster_export[f"cluster_{cluster_id}"] = {
                                        'cluster_label': cluster.cluster_label,
                                        'size': cluster.size,
                                        'avg_score': cluster.avg_score,
                                        'companies': cluster.companies,
                                        'common_themes': insights['cluster_info']['common_themes'],
                                        'recommendations': insights['recommendations'],
                                        'next_steps': insights['next_steps']
                                    }
                                
                                cluster_json = json.dumps(cluster_export, indent=2)
                                st.download_button(
                                    label="📊 Download Cluster Analysis",
                                    data=cluster_json,
                                    file_name="cluster_analysis.json",
                                    mime="application/json"
                                )
                                
                            else:
                                st.error("No clusters were generated. Try adjusting the parameters or method.")
                                
                        except Exception as e:
                            st.error(f"Clustering failed: {e}")
                            st.exception(e)
            
            elif data and len(data) < 3:
                st.warning("Need at least 3 scored leads to perform clustering analysis")
            
            else:
                st.error("No valid data found in the uploaded file")
    
    elif mode == "Team Analytics":
        st.header("📊 Team Analytics & Performance")
        st.markdown("Comprehensive insights into team performance, trends, and lead quality over time")
        
        # Initialize analytics engine
        try:
            analytics_engine = TeamAnalyticsEngine()
        except Exception as e:
            st.error(f"Failed to initialize analytics engine: {e}")
            return
        
        # Time period selection
        col1, col2, col3 = st.columns(3)
        
        with col1:
            time_period = st.selectbox(
                "Analysis Period:",
                [7, 14, 30, 60, 90],
                index=2,
                help="Number of days to analyze"
            )
        
        with col2:
            if st.button("🔄 Refresh Data"):
                st.cache_data.clear()
        
        with col3:
            # Record session option
            uploaded_results = st.file_uploader(
                "Add Results to Analytics",
                type=['json'],
                help="Upload scored results to add to team analytics"
            )
        
        if uploaded_results:
            try:
                content = uploaded_results.read()
                results_data = json.loads(content)
                
                # Get user name for session tracking
                user_name = st.text_input("Your Name:", value="dashboard_user")
                
                if st.button("📈 Record Session"):
                    session_id = analytics_engine.record_processing_session(
                        results=results_data,
                        user=user_name,
                        input_file=uploaded_results.name,
                        processing_time=0.0
                    )
                    st.success(f"✅ Session recorded: {session_id}")
                    st.cache_data.clear()
                    
            except Exception as e:
                st.error(f"Error processing uploaded results: {e}")
        
        # Get performance metrics
        try:
            metrics = analytics_engine.get_team_performance_metrics(days_back=time_period)
            insights = analytics_engine.get_lead_scoring_insights(days_back=time_period)
            
            if 'error' in metrics:
                st.warning("📋 No team data available yet")
                st.info("👆 Upload some scored results above to start building team analytics")
                
                # Show demo data option
                if st.button("🎲 Generate Demo Data"):
                    # Create some demo sessions
                    demo_results = [
                        {
                            "company": "DemoTech",
                            "domain": "demo.com",
                            "score": 82,
                            "priority": "High",
                            "breakdown": {
                                "industry_fit": 17,
                                "scale_indicators": 15,
                                "platform_maturity": 16,
                                "growth_churn_challenges": 16,
                                "revenue_sophistication": 18
                            }
                        },
                        {
                            "company": "StartupCorp",
                            "domain": "startup.io",
                            "score": 65,
                            "priority": "Medium",
                            "breakdown": {
                                "industry_fit": 13,
                                "scale_indicators": 12,
                                "platform_maturity": 14,
                                "growth_churn_challenges": 13,
                                "revenue_sophistication": 13
                            }
                        }
                    ]
                    
                    analytics_engine.record_processing_session(
                        results=demo_results,
                        user="demo_user",
                        input_file="demo_data.csv",
                        model_used="gpt-4-turbo",
                        template_used="recurly_template.txt"
                    )
                    
                    st.success("✅ Demo data created! Refresh to see analytics.")
                    st.rerun()
                    
                return
            
            # Executive Summary
            st.header("📊 Executive Summary")
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric(
                    "Total Sessions",
                    metrics['total_sessions'],
                    help="Number of processing sessions in period"
                )
            
            with col2:
                st.metric(
                    "Leads Processed",
                    metrics['total_leads_processed'],
                    help="Total leads processed across all sessions"
                )
            
            with col3:
                st.metric(
                    "Success Rate",
                    f"{metrics['avg_success_rate']*100:.1f}%",
                    help="Average processing success rate"
                )
            
            with col4:
                st.metric(
                    "High Priority Leads",
                    metrics['total_high_priority'],
                    help="Number of high-priority leads found"
                )
            
            with col5:
                st.metric(
                    "Avg Processing Time",
                    f"{metrics['avg_processing_time']:.1f}s",
                    help="Average time per session"
                )
            
            # Performance Charts
            st.header("📈 Performance Analytics")
            
            try:
                charts = analytics_engine.create_performance_charts(days_back=time_period)
                
                # Daily trends
                if 'daily_trends' in charts:
                    st.plotly_chart(charts['daily_trends'], use_container_width=True)
                
                col1, col2 = st.columns(2)
                
                # User performance
                if 'user_performance' in charts:
                    with col1:
                        st.plotly_chart(charts['user_performance'], use_container_width=True)
                
                # Score distribution
                if 'score_distribution' in charts:
                    with col2:
                        st.plotly_chart(charts['score_distribution'], use_container_width=True)
                
                # Dimension correlation
                if 'dimension_correlation' in charts:
                    st.plotly_chart(charts['dimension_correlation'], use_container_width=True)
                    
            except Exception as e:
                st.warning(f"Could not generate charts: {e}")
            
            # Team Performance Details
            st.header("👥 Team Performance")
            
            if 'user_performance' in metrics and metrics['user_performance']:
                user_data = []
                for user, stats in metrics['user_performance'].items():
                    user_data.append({
                        'User': user,
                        'Sessions': stats['session_id'],
                        'Leads Processed': stats['processed_leads'],
                        'Avg Success Rate': f"{stats['success_rate']*100:.1f}%",
                        'Avg Score': f"{stats['avg_score']:.1f}",
                        'High Priority Finds': stats['high_priority_count']
                    })
                
                user_df = pd.DataFrame(user_data)
                st.dataframe(user_df, use_container_width=True)
            else:
                st.info("No user performance data available")
            
            # Model & Template Analysis
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🤖 Model Performance")
                if 'model_performance' in metrics and metrics['model_performance']:
                    model_data = []
                    for model, stats in metrics['model_performance'].items():
                        model_data.append({
                            'Model': model,
                            'Sessions': stats['session_id'],
                            'Avg Score': f"{stats['avg_score']:.1f}",
                            'Success Rate': f"{stats['success_rate']*100:.1f}%",
                            'Avg Time': f"{stats['processing_time']:.1f}s"
                        })
                    
                    model_df = pd.DataFrame(model_data)
                    st.dataframe(model_df, use_container_width=True)
                else:
                    st.info("No model performance data")
            
            with col2:
                st.subheader("📝 Template Performance")
                if 'template_performance' in metrics and metrics['template_performance']:
                    template_data = []
                    for template, stats in metrics['template_performance'].items():
                        template_data.append({
                            'Template': template,
                            'Sessions': stats['session_id'],
                            'Avg Score': f"{stats['avg_score']:.1f}",
                            'Success Rate': f"{stats['success_rate']*100:.1f}%"
                        })
                    
                    template_df = pd.DataFrame(template_data)
                    st.dataframe(template_df, use_container_width=True)
                else:
                    st.info("No template performance data")
            
            # Lead Quality Insights
            st.header("🎯 Lead Quality Insights")
            
            if 'error' not in insights:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("🏆 Top Performing Companies")
                    if 'top_companies' in insights:
                        top_df = pd.DataFrame(insights['top_companies'])
                        st.dataframe(top_df, use_container_width=True)
                
                with col2:
                    st.subheader("📊 Score Quality Distribution")
                    if 'score_distribution' in insights:
                        dist = insights['score_distribution']
                        total = sum(dist.values())
                        
                        if total > 0:
                            st.write(f"**High Quality (75+):** {dist['high']} ({dist['high']/total*100:.1f}%)")
                            st.write(f"**Medium Quality (50-74):** {dist['medium']} ({dist['medium']/total*100:.1f}%)")
                            st.write(f"**Low Quality (<50):** {dist['low']} ({dist['low']/total*100:.1f}%)")
                
                # Dimension insights
                st.subheader("🔍 Scoring Dimension Analysis")
                if 'dimension_analysis' in insights:
                    dim_data = []
                    for dim, stats in insights['dimension_analysis'].items():
                        dim_data.append({
                            'Dimension': dim.replace('_', ' ').title(),
                            'Average Score': f"{stats['mean']:.1f}",
                            'Std Deviation': f"{stats['std']:.2f}",
                            'Correlation with Final Score': f"{stats['correlation_with_score']:.3f}"
                        })
                    
                    dim_df = pd.DataFrame(dim_data)
                    st.dataframe(dim_df, use_container_width=True)
            
            # Recommendations
            st.header("💡 AI Recommendations")
            
            try:
                report = analytics_engine.generate_performance_report(days_back=time_period)
                if 'recommendations' in report:
                    for i, rec in enumerate(report['recommendations'], 1):
                        st.write(f"{i}. {rec}")
                else:
                    st.info("No specific recommendations at this time")
            except Exception as e:
                st.warning(f"Could not generate recommendations: {e}")
            
            # Export Options
            st.header("📥 Export & Reports")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📊 Generate Full Report"):
                    try:
                        report = analytics_engine.generate_performance_report(days_back=time_period)
                        report_json = json.dumps(report, indent=2, default=str)
                        
                        st.download_button(
                            label="📄 Download Performance Report (JSON)",
                            data=report_json,
                            file_name=f"team_performance_report_{time_period}d.json",
                            mime="application/json"
                        )
                        
                        st.success("✅ Report generated successfully!")
                    except Exception as e:
                        st.error(f"Failed to generate report: {e}")
            
            with col2:
                if st.button("📈 Export Analytics Data"):
                    try:
                        # Export session and lead data as CSV
                        sessions_df = analytics_engine.db.get_sessions(time_period)
                        leads_df = analytics_engine.db.get_leads(time_period)
                        
                        sessions_csv = sessions_df.to_csv(index=False)
                        leads_csv = leads_df.to_csv(index=False)
                        
                        st.download_button(
                            label="📊 Download Sessions Data (CSV)",
                            data=sessions_csv,
                            file_name=f"sessions_data_{time_period}d.csv",
                            mime="text/csv"
                        )
                        
                        st.download_button(
                            label="🎯 Download Leads Data (CSV)",
                            data=leads_csv,
                            file_name=f"leads_data_{time_period}d.csv",
                            mime="text/csv"
                        )
                    except Exception as e:
                        st.error(f"Failed to export data: {e}")
            
        except Exception as e:
            st.error(f"Analytics error: {e}")
            st.exception(e)

if __name__ == "__main__":
    # Check authentication first
    if not require_authentication():
        st.stop()
    
    # Handle authenticated user navigation
    if handle_authenticated_navigation():
        st.stop()
    
    # Run main dashboard
    main()
