#!/usr/bin/env python3
"""
CLI for lead clustering analysis
"""

import argparse
import json
import sys
from pathlib import Path
from analysis.lead_clustering import LeadClusterer

def cluster_leads(args):
    """Cluster leads from JSON file"""
    print(f"Loading leads from {args.input}...")
    
    try:
        with open(args.input, 'r') as f:
            leads_data = json.load(f)
        
        if not leads_data:
            print("No leads found in input file")
            return
        
        print(f"Found {len(leads_data)} leads")
        
        # Initialize clusterer
        clusterer = LeadClusterer(random_state=args.seed)
        
        # Perform clustering
        clusters = clusterer.cluster_leads(
            leads_data, 
            method=args.method, 
            n_clusters=args.clusters
        )
        
        if not clusters:
            print("No clusters generated")
            return
        
        # Print summary
        clusterer.print_cluster_summary()
        
        # Show detailed insights if requested
        if args.detailed:
            print(f"\n{'='*60}")
            print("DETAILED CLUSTER INSIGHTS")
            print(f"{'='*60}")
            
            for cluster_id in sorted(clusters.keys()):
                insights = clusterer.get_cluster_insights(cluster_id)
                cluster_info = insights['cluster_info']
                
                print(f"\n📊 CLUSTER {cluster_id}: {cluster_info['cluster_label']}")
                print(f"{'='*50}")
                
                # Basic info
                print(f"Companies ({cluster_info['size']}): {', '.join(cluster_info['companies'])}")
                print(f"Average Score: {cluster_info['avg_score']:.1f}/100")
                print(f"Common Themes: {', '.join(cluster_info['common_themes'][:5])}")
                
                # Characteristics
                chars = cluster_info['characteristics']
                if 'score_stats' in chars:
                    stats = chars['score_stats']
                    print(f"Score Range: {stats['min']:.1f} - {stats['max']:.1f} (±{stats['std']:.1f})")
                
                if 'priority_distribution' in chars:
                    priorities = chars['priority_distribution']
                    print(f"Priority Mix: {priorities}")
                
                # Recommendations
                print(f"\n🎯 RECOMMENDATIONS:")
                for i, rec in enumerate(insights['recommendations'], 1):
                    print(f"  {i}. {rec}")
                
                print(f"\n📋 NEXT STEPS:")
                for i, step in enumerate(insights['next_steps'], 1):
                    print(f"  {i}. {step}")
        
        # Export results if requested
        if args.output:
            clusterer.export_clusters(args.output)
            print(f"\nCluster results exported to {args.output}")
        
        # Generate summary stats
        print(f"\n📈 CLUSTERING SUMMARY")
        print(f"{'='*30}")
        total_companies = sum(cluster.size for cluster in clusters.values())
        avg_cluster_size = total_companies / len(clusters) if clusters else 0
        highest_scoring_cluster = max(clusters.values(), key=lambda x: x.avg_score)
        
        print(f"Total Clusters: {len(clusters)}")
        print(f"Average Cluster Size: {avg_cluster_size:.1f} companies")
        print(f"Highest Value Cluster: {highest_scoring_cluster.cluster_label} ({highest_scoring_cluster.avg_score:.1f} avg score)")
        
        # Show clustering method performance
        print(f"\nMethod: {args.method}")
        if args.clusters:
            print(f"Clusters: {args.clusters} (specified)")
        else:
            print(f"Clusters: {len(clusters)} (auto-optimized)")
        
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{args.input}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def compare_methods(args):
    """Compare different clustering methods"""
    print(f"Loading leads from {args.input}...")
    
    try:
        with open(args.input, 'r') as f:
            leads_data = json.load(f)
        
        if len(leads_data) < 4:
            print("Need at least 4 leads for method comparison")
            return
        
        methods = ['kmeans', 'hierarchical', 'dbscan']
        results = {}
        
        print(f"\nComparing clustering methods on {len(leads_data)} leads...")
        print("=" * 60)
        
        for method in methods:
            print(f"\nTesting {method.upper()}...")
            
            clusterer = LeadClusterer(random_state=args.seed)
            
            try:
                clusters = clusterer.cluster_leads(leads_data, method=method)
                
                if clusters:
                    results[method] = {
                        'num_clusters': len(clusters),
                        'avg_score': sum(c.avg_score for c in clusters.values()) / len(clusters),
                        'total_companies': sum(c.size for c in clusters.values()),
                        'cluster_sizes': [c.size for c in clusters.values()],
                        'cluster_labels': [c.cluster_label for c in clusters.values()]
                    }
                    
                    print(f"  ✅ {len(clusters)} clusters created")
                    print(f"  📊 Average cluster score: {results[method]['avg_score']:.1f}")
                    print(f"  📈 Cluster sizes: {results[method]['cluster_sizes']}")
                else:
                    print(f"  ❌ No clusters generated")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        # Summary comparison
        print(f"\n🏆 METHOD COMPARISON SUMMARY")
        print("=" * 40)
        
        if results:
            for method, data in results.items():
                print(f"\n{method.upper()}:")
                print(f"  Clusters: {data['num_clusters']}")
                print(f"  Avg Score: {data['avg_score']:.1f}")
                print(f"  Cluster Balance: {data['cluster_sizes']}")
            
            # Recommend best method
            best_method = max(results.items(), key=lambda x: x[1]['avg_score'])
            print(f"\n🎯 RECOMMENDATION: Use '{best_method[0]}' method")
            print(f"   (Highest average cluster score: {best_method[1]['avg_score']:.1f})")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def analyze_existing_clusters(args):
    """Analyze existing cluster results"""
    try:
        with open(args.input, 'r') as f:
            cluster_data = json.load(f)
        
        print(f"📊 CLUSTER ANALYSIS REPORT")
        print("=" * 50)
        
        total_clusters = len(cluster_data)
        total_companies = sum(data['size'] for data in cluster_data.values())
        
        print(f"Total Clusters: {total_clusters}")
        print(f"Total Companies: {total_companies}")
        print(f"Average Cluster Size: {total_companies/total_clusters:.1f}")
        
        # Sort by score
        sorted_clusters = sorted(cluster_data.items(), 
                               key=lambda x: x[1]['avg_score'], reverse=True)
        
        print(f"\n🏆 TOP PERFORMING CLUSTERS:")
        for i, (cluster_id, data) in enumerate(sorted_clusters[:3], 1):
            print(f"{i}. {data['cluster_label']} (Score: {data['avg_score']:.1f})")
            print(f"   Companies: {', '.join(data['companies'][:3])}")
            print(f"   Themes: {', '.join(data['common_themes'][:3])}")
        
        # Size distribution
        sizes = [data['size'] for data in cluster_data.values()]
        print(f"\n📏 CLUSTER SIZE DISTRIBUTION:")
        print(f"   Smallest: {min(sizes)} companies")
        print(f"   Largest: {max(sizes)} companies")
        print(f"   Average: {sum(sizes)/len(sizes):.1f} companies")
        
        # Theme analysis
        all_themes = []
        for data in cluster_data.values():
            all_themes.extend(data['common_themes'][:3])  # Top 3 from each cluster
        
        from collections import Counter
        theme_counts = Counter(all_themes)
        
        print(f"\n🔍 MOST COMMON THEMES:")
        for theme, count in theme_counts.most_common(5):
            print(f"   '{theme}' - appears in {count} clusters")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='Lead clustering analysis for Recursor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli_clustering.py cluster --input data/scored.json --output clusters.json
  python cli_clustering.py cluster --input data/scored.json --method hierarchical --detailed
  python cli_clustering.py compare --input data/scored.json
  python cli_clustering.py analyze --input clusters.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Cluster command
    cluster_cmd = subparsers.add_parser('cluster', help='Cluster leads')
    cluster_cmd.add_argument('--input', required=True, help='Input JSON file with scored leads')
    cluster_cmd.add_argument('--output', help='Output JSON file for cluster results')
    cluster_cmd.add_argument('--method', choices=['kmeans', 'hierarchical', 'dbscan'], 
                           default='kmeans', help='Clustering method')
    cluster_cmd.add_argument('--clusters', type=int, help='Number of clusters (auto-detect if not specified)')
    cluster_cmd.add_argument('--detailed', action='store_true', help='Show detailed cluster insights')
    cluster_cmd.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility')
    
    # Compare methods command
    compare_cmd = subparsers.add_parser('compare', help='Compare clustering methods')
    compare_cmd.add_argument('--input', required=True, help='Input JSON file with scored leads')
    compare_cmd.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility')
    
    # Analyze existing clusters command
    analyze_cmd = subparsers.add_parser('analyze', help='Analyze existing cluster results')
    analyze_cmd.add_argument('--input', required=True, help='Input JSON file with cluster results')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Route commands
    if args.command == 'cluster':
        cluster_leads(args)
    elif args.command == 'compare':
        compare_methods(args)
    elif args.command == 'analyze':
        analyze_existing_clusters(args)

if __name__ == "__main__":
    main()
