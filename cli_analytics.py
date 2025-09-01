#!/usr/bin/env python3
"""
Team Analytics CLI for Recursor
Generate performance reports, insights, and team analytics
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

from analytics.team_analytics import TeamAnalyticsEngine, load_and_record_session

def record_session(args):
    """Record a processing session from results file"""
    print(f"📈 Recording session from {args.input}")
    
    try:
        db_path = args.db_path if hasattr(args, 'db_path') and args.db_path else "analytics/team_analytics.db"
        engine = TeamAnalyticsEngine(db_path)
        
        session_id = load_and_record_session(
            results_file=args.input,
            user=args.user,
            analytics_engine=engine
        )
        
        if session_id:
            print(f"✅ Session recorded successfully: {session_id}")
        else:
            print("❌ Failed to record session")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error recording session: {e}")
        sys.exit(1)

def generate_report(args):
    """Generate team performance report"""
    print(f"📊 Generating team performance report ({args.days} days)")
    
    try:
        engine = TeamAnalyticsEngine(args.db_path if hasattr(args, 'db_path') and args.db_path else "analytics/team_analytics.db")
        
        report = engine.generate_performance_report(days_back=args.days)
        
        if 'error' in report:
            print(f"❌ {report['error']}")
            print("💡 Try recording some sessions first with: python cli_analytics.py record --input your_results.json")
            sys.exit(1)
        
        # Save report
        report_path = args.output or f"team_report_{args.days}d_{datetime.now().strftime('%Y%m%d')}.json"
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"💾 Report saved to: {report_path}")
        
        # Print executive summary
        print("\n📋 EXECUTIVE SUMMARY")
        print("=" * 40)
        summary = report['executive_summary']
        print(f"Sessions: {summary['total_sessions']}")
        print(f"Leads Processed: {summary['total_leads']}")  
        print(f"Success Rate: {summary['success_rate']}")
        print(f"High Priority Leads: {summary['high_priority_leads']}")
        print(f"Avg Processing Time: {summary['avg_processing_time']}")
        
        # Print recommendations
        if 'recommendations' in report and report['recommendations']:
            print(f"\n💡 KEY RECOMMENDATIONS")
            print("=" * 30)
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"{i}. {rec}")
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        sys.exit(1)

def show_metrics(args):
    """Show current team metrics"""
    print(f"📊 Team Metrics (Last {args.days} days)")
    
    try:
        engine = TeamAnalyticsEngine(args.db_path if hasattr(args, 'db_path') and args.db_path else "analytics/team_analytics.db")
        
        metrics = engine.get_team_performance_metrics(days_back=args.days)
        insights = engine.get_lead_scoring_insights(days_back=args.days)
        
        if 'error' in metrics:
            print(f"❌ {metrics['error']}")
            return
        
        print("\n🏢 OVERALL METRICS")
        print("=" * 25)
        print(f"Total Sessions: {metrics['total_sessions']}")
        print(f"Leads Processed: {metrics['total_leads_processed']}")
        print(f"Success Rate: {metrics['avg_success_rate']*100:.1f}%")
        print(f"High Priority Leads: {metrics['total_high_priority']}")
        print(f"Avg Processing Time: {metrics['avg_processing_time']:.1f}s")
        
        # User performance
        if 'user_performance' in metrics and metrics['user_performance']:
            print(f"\n👥 USER PERFORMANCE")
            print("=" * 20)
            for user, stats in metrics['user_performance'].items():
                print(f"{user}:")
                print(f"  Sessions: {stats['session_id']}")
                print(f"  Leads: {stats['processed_leads']}")
                print(f"  Avg Score: {stats['avg_score']:.1f}")
                print(f"  Success Rate: {stats['success_rate']*100:.1f}%")
        
        # Model performance
        if 'model_performance' in metrics and metrics['model_performance']:
            print(f"\n🤖 MODEL PERFORMANCE")
            print("=" * 20)
            for model, stats in metrics['model_performance'].items():
                print(f"{model}:")
                print(f"  Sessions: {stats['session_id']}")
                print(f"  Avg Score: {stats['avg_score']:.1f}")
                print(f"  Success Rate: {stats['success_rate']*100:.1f}%")
        
        # Lead insights
        if 'error' not in insights:
            print(f"\n🎯 LEAD INSIGHTS")
            print("=" * 15)
            if 'score_distribution' in insights:
                dist = insights['score_distribution']
                total = sum(dist.values())
                if total > 0:
                    print(f"High Quality (75+): {dist['high']} ({dist['high']/total*100:.1f}%)")
                    print(f"Medium Quality (50-74): {dist['medium']} ({dist['medium']/total*100:.1f}%)")
                    print(f"Low Quality (<50): {dist['low']} ({dist['low']/total*100:.1f}%)")
            
            if 'top_companies' in insights:
                print(f"\n🏆 TOP COMPANIES:")
                for company in insights['top_companies'][:5]:
                    print(f"  {company['company']}: {company['score']}/100 ({company['priority']})")
        
    except Exception as e:
        print(f"❌ Error showing metrics: {e}")
        sys.exit(1)

def export_data(args):
    """Export analytics data to CSV"""
    print(f"📤 Exporting analytics data ({args.days} days)")
    
    try:
        engine = TeamAnalyticsEngine(args.db_path if hasattr(args, 'db_path') and args.db_path else "analytics/team_analytics.db")
        
        # Get data
        sessions_df = engine.db.get_sessions(args.days)
        leads_df = engine.db.get_leads(args.days)
        
        if sessions_df.empty and leads_df.empty:
            print("❌ No data available for export")
            return
        
        # Generate filenames
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if not sessions_df.empty:
            sessions_file = f"sessions_{args.days}d_{timestamp}.csv"
            sessions_df.to_csv(sessions_file, index=False)
            print(f"💾 Sessions data: {sessions_file}")
        
        if not leads_df.empty:
            leads_file = f"leads_{args.days}d_{timestamp}.csv"
            leads_df.to_csv(leads_file, index=False)  
            print(f"💾 Leads data: {leads_file}")
        
        print("✅ Export complete!")
        
    except Exception as e:
        print(f"❌ Error exporting data: {e}")
        sys.exit(1)

def list_sessions(args):
    """List recent processing sessions"""
    print(f"📋 Recent Sessions (Last {args.days} days)")
    
    try:
        engine = TeamAnalyticsEngine(args.db_path if hasattr(args, 'db_path') and args.db_path else "analytics/team_analytics.db")
        
        sessions_df = engine.db.get_sessions(args.days)
        
        if sessions_df.empty:
            print("❌ No sessions found")
            return
        
        print("=" * 80)
        print(f"{'Session ID':<25} {'User':<15} {'Date':<12} {'Leads':<8} {'Score':<8} {'Success':<8}")
        print("=" * 80)
        
        for _, session in sessions_df.head(args.limit).iterrows():
            date_str = session['timestamp'].strftime('%Y-%m-%d') if hasattr(session['timestamp'], 'strftime') else str(session['timestamp'])[:10]
            
            print(f"{session['session_id']:<25} {session['user']:<15} {date_str:<12} "
                  f"{session['processed_leads']:<8} {session['avg_score']:<8.1f} {session['success_rate']*100:<7.1f}%")
        
        print(f"\nShowing {min(len(sessions_df), args.limit)} of {len(sessions_df)} sessions")
        
    except Exception as e:
        print(f"❌ Error listing sessions: {e}")
        sys.exit(1)

def cleanup_data(args):
    """Clean up old analytics data"""
    print(f"🧹 Cleaning analytics data older than {args.older_than} days")
    
    try:
        engine = TeamAnalyticsEngine(args.db_path if hasattr(args, 'db_path') and args.db_path else "analytics/team_analytics.db")
        
        # This would require additional cleanup methods in the analytics engine
        # For now, just show what would be cleaned
        all_sessions = engine.db.get_sessions(days_back=365)  # Get all sessions
        cutoff_date = datetime.now() - pd.Timedelta(days=args.older_than)
        
        if not all_sessions.empty:
            old_sessions = all_sessions[all_sessions['timestamp'] < cutoff_date]
            print(f"Found {len(old_sessions)} sessions older than {args.older_than} days")
            
            if args.confirm:
                # In a real implementation, this would delete the old data
                print("🚧 Cleanup functionality not yet implemented in database layer")
                print("💡 Consider manually managing the SQLite database file for now")
            else:
                print("Use --confirm to actually delete the old data")
        else:
            print("No old data to clean up")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        sys.exit(1)

def create_demo_data(args):
    """Create demo analytics data"""
    print("🎲 Creating demo analytics data...")
    
    try:
        engine = TeamAnalyticsEngine(args.db_path if hasattr(args, 'db_path') and args.db_path else "analytics/team_analytics.db")
        
        # Create several demo sessions
        demo_sessions = [
            {
                "results": [
                    {
                        "company": "TechCorp",
                        "domain": "techcorp.com",
                        "score": 88,
                        "priority": "High",
                        "breakdown": {
                            "industry_fit": 18,
                            "scale_indicators": 17,
                            "platform_maturity": 18,
                            "growth_churn_challenges": 17,
                            "revenue_sophistication": 18
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
                    }
                ],
                "user": "alice",
                "model": "gpt-4-turbo",
                "template": "recurly_template.txt"
            },
            {
                "results": [
                    {
                        "company": "GrowthCo",
                        "domain": "growth.co",
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
                ],
                "user": "bob",
                "model": "gpt-4",
                "template": "recurly_template.txt"
            },
            {
                "results": [
                    {
                        "company": "SmallBiz",
                        "domain": "small.biz",
                        "score": 45,
                        "priority": "Low",
                        "breakdown": {
                            "industry_fit": 9,
                            "scale_indicators": 8,
                            "platform_maturity": 10,
                            "growth_churn_challenges": 9,
                            "revenue_sophistication": 9
                        }
                    }
                ],
                "user": "charlie",
                "model": "gpt-3.5-turbo",
                "template": "basic_template.txt"
            }
        ]
        
        for i, session_data in enumerate(demo_sessions):
            session_id = engine.record_processing_session(
                results=session_data["results"],
                user=session_data["user"],
                input_file=f"demo_batch_{i+1}.csv",
                model_used=session_data["model"],
                template_used=session_data["template"],
                processing_time=10.0 + i * 2.5
            )
            print(f"✅ Created demo session: {session_id}")
        
        print(f"\n🎉 Demo data created! Use 'python cli_analytics.py metrics' to see results")
        
    except Exception as e:
        print(f"❌ Error creating demo data: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='Team Analytics CLI for Recursor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Record a processing session
  python cli_analytics.py record --input scored_results.json --user alice

  # Generate performance report
  python cli_analytics.py report --days 30 --output team_report.json

  # Show current metrics
  python cli_analytics.py metrics --days 7

  # Export data for external analysis  
  python cli_analytics.py export --days 60

  # List recent sessions
  python cli_analytics.py sessions --days 14 --limit 10

  # Create demo data for testing
  python cli_analytics.py demo
        """
    )
    
    # Global options
    parser.add_argument('--db-path', help='Path to analytics database file')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Record session command
    record_cmd = subparsers.add_parser('record', help='Record a processing session')
    record_cmd.add_argument('--input', required=True, help='Input JSON results file')
    record_cmd.add_argument('--user', default='cli_user', help='User name for session tracking')
    
    # Generate report command
    report_cmd = subparsers.add_parser('report', help='Generate team performance report')
    report_cmd.add_argument('--days', type=int, default=30, help='Days back to analyze')
    report_cmd.add_argument('--output', help='Output file path (default: auto-generated)')
    
    # Show metrics command
    metrics_cmd = subparsers.add_parser('metrics', help='Show current team metrics')
    metrics_cmd.add_argument('--days', type=int, default=7, help='Days back to analyze')
    
    # Export data command
    export_cmd = subparsers.add_parser('export', help='Export analytics data to CSV')
    export_cmd.add_argument('--days', type=int, default=30, help='Days back to export')
    
    # List sessions command
    sessions_cmd = subparsers.add_parser('sessions', help='List recent processing sessions')
    sessions_cmd.add_argument('--days', type=int, default=14, help='Days back to show')
    sessions_cmd.add_argument('--limit', type=int, default=20, help='Maximum sessions to show')
    
    # Cleanup command
    cleanup_cmd = subparsers.add_parser('cleanup', help='Clean up old analytics data')
    cleanup_cmd.add_argument('--older-than', type=int, default=90, help='Delete data older than N days')
    cleanup_cmd.add_argument('--confirm', action='store_true', help='Confirm deletion')
    
    # Demo data command
    demo_cmd = subparsers.add_parser('demo', help='Create demo analytics data')
    
    args = parser.parse_args()
    
    # Route commands
    if args.command == 'record':
        record_session(args)
    elif args.command == 'report':
        generate_report(args)
    elif args.command == 'metrics':
        show_metrics(args)
    elif args.command == 'export':
        export_data(args)
    elif args.command == 'sessions':
        list_sessions(args)
    elif args.command == 'cleanup':
        cleanup_data(args)
    elif args.command == 'demo':
        create_demo_data(args)
    else:
        parser.print_help()
        print("\n❌ Error: Please specify a command")
        sys.exit(1)

if __name__ == "__main__":
    main()
