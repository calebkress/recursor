#!/usr/bin/env python3
"""
Enhanced Batch Processing CLI for Recursor
High-performance batch operations with concurrent processing, caching, and resumption
"""

import argparse
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# Import our modules
from enrich.serp_api import LeadEnricher
from score.scorer import LeadScorer
from analysis.lead_clustering import LeadClusterer
from processing.batch_processor import BatchProcessor, BatchJob, create_enrichment_processor, create_scoring_processor
from config.config_manager import get_config, ConfigManager, setup_logging


def batch_enrich(args):
    """Batch enrichment with concurrent processing"""
    print(f"🔍 Starting batch enrichment from {args.input}")
    
    # Load configuration
    config = get_config(args.environment)
    logger = config.setup_logging()
    
    # Initialize processor and enricher
    processor = BatchProcessor(config)
    enricher = LeadEnricher()
    
    # Create jobs from CSV
    jobs = processor.create_jobs_from_csv(args.input)
    
    if not jobs:
        print("❌ No jobs created from input file")
        sys.exit(1)
    
    print(f"📋 Created {len(jobs)} enrichment jobs")
    
    # Create enrichment processor function
    enrichment_processor = create_enrichment_processor(enricher)
    
    # Process batch
    batch_id = args.batch_id or f"enrich_{Path(args.input).stem}"
    
    try:
        processed_jobs = processor.process_batch(
            jobs,
            enrichment_processor,
            batch_id=batch_id,
            resume=args.resume
        )
        
        # Export results
        processor.export_results(processed_jobs, args.output, format="json")
        
        # Generate report if requested
        if args.report:
            report_path = args.output.replace('.json', '_report.md')
            processor.export_results(processed_jobs, report_path, format="report")
            print(f"📊 Processing report saved to {report_path}")
        
        # Clean up checkpoint
        if not args.keep_checkpoint:
            processor.checkpoint.delete_checkpoint(batch_id)
        
        # Statistics
        completed = sum(1 for j in processed_jobs if j.status == 'completed')
        failed = sum(1 for j in processed_jobs if j.status == 'failed')
        
        print(f"\n✅ Batch enrichment complete!")
        print(f"   Processed: {completed}/{len(jobs)} companies")
        print(f"   Success rate: {(completed/len(jobs)*100):.1f}%")
        print(f"   Results saved to: {args.output}")
        
    except KeyboardInterrupt:
        print(f"\n⏸️  Batch processing interrupted. Resume with: --batch-id {batch_id} --resume")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Batch enrichment failed: {e}")
        print(f"❌ Batch enrichment failed: {e}")
        sys.exit(1)


def batch_score(args):
    """Batch scoring with concurrent processing"""
    print(f"🧠 Starting batch scoring from {args.input}")
    
    # Load configuration
    config = get_config(args.environment)
    logger = config.setup_logging()
    
    # Load enriched data
    with open(args.input, 'r') as f:
        enriched_data = json.load(f)
    
    if not enriched_data:
        print("❌ No enriched data found in input file")
        sys.exit(1)
    
    # Convert to batch jobs
    jobs = []
    for data in enriched_data:
        job = BatchJob(
            company=data.get('company', ''),
            domain=data.get('domain', ''),
            result=data  # Store enrichment data as result
        )
        jobs.append(job)
    
    print(f"📋 Created {len(jobs)} scoring jobs")
    
    # Initialize processor and scorer
    processor = BatchProcessor(config)
    scorer = LeadScorer(model=args.model)
    
    # Create scoring processor function
    scoring_processor = create_scoring_processor(scorer, template_name=args.template)
    
    # Process batch
    batch_id = args.batch_id or f"score_{Path(args.input).stem}"
    
    try:
        processed_jobs = processor.process_batch(
            jobs,
            scoring_processor,
            batch_id=batch_id,
            resume=args.resume
        )
        
        # Export results
        processor.export_results(processed_jobs, args.output, format="json")
        
        # Generate report if requested
        if args.report:
            report_path = args.output.replace('.json', '_report.md')
            processor.export_results(processed_jobs, report_path, format="report")
            print(f"📊 Processing report saved to {report_path}")
        
        # Clean up checkpoint
        if not args.keep_checkpoint:
            processor.checkpoint.delete_checkpoint(batch_id)
        
        # Statistics
        completed = sum(1 for j in processed_jobs if j.status == 'completed')
        failed = sum(1 for j in processed_jobs if j.status == 'failed')
        
        print(f"\n✅ Batch scoring complete!")
        print(f"   Processed: {completed}/{len(jobs)} companies")
        print(f"   Success rate: {(completed/len(jobs)*100):.1f}%")
        print(f"   Results saved to: {args.output}")
        
        # Show top scoring companies
        if completed > 0:
            completed_jobs = [j for j in processed_jobs if j.status == 'completed']
            sorted_jobs = sorted(completed_jobs, key=lambda x: x.result.get('score', 0), reverse=True)
            
            print(f"\n🏆 Top 3 Scoring Companies:")
            for i, job in enumerate(sorted_jobs[:3], 1):
                score = job.result.get('score', 0)
                priority = job.result.get('priority', 'N/A')
                print(f"   {i}. {job.company}: {score}/100 ({priority} Priority)")
        
    except KeyboardInterrupt:
        print(f"\n⏸️  Batch processing interrupted. Resume with: --batch-id {batch_id} --resume")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Batch scoring failed: {e}")
        print(f"❌ Batch scoring failed: {e}")
        sys.exit(1)


def batch_full_pipeline(args):
    """Run complete pipeline with batch processing"""
    print(f"🚀 Starting full batch pipeline from {args.input}")
    
    # Load configuration
    config = get_config(args.environment)
    logger = config.setup_logging()
    
    # Initialize components
    processor = BatchProcessor(config)
    enricher = LeadEnricher()
    scorer = LeadScorer(model=args.model)
    
    # Step 1: Enrichment
    print("\n=== STEP 1: BATCH ENRICHMENT ===")
    
    # Create enrichment jobs
    enrich_jobs = processor.create_jobs_from_csv(args.input)
    print(f"📋 Created {len(enrich_jobs)} enrichment jobs")
    
    enrichment_processor = create_enrichment_processor(enricher)
    enrich_batch_id = f"pipeline_enrich_{Path(args.input).stem}"
    
    try:
        enriched_jobs = processor.process_batch(
            enrich_jobs,
            enrichment_processor,
            batch_id=enrich_batch_id,
            resume=args.resume
        )
        
        # Filter successful enrichments
        successful_enrichments = [j for j in enriched_jobs if j.status == 'completed']
        print(f"✅ Enrichment complete: {len(successful_enrichments)} companies")
        
        if not successful_enrichments:
            print("❌ No successful enrichments, stopping pipeline")
            sys.exit(1)
        
        # Step 2: Scoring
        print("\n=== STEP 2: BATCH SCORING ===")
        
        # Convert enriched results to scoring jobs
        score_jobs = []
        for job in successful_enrichments:
            score_job = BatchJob(
                company=job.company,
                domain=job.domain,
                result=job.result  # Use enrichment result
            )
            score_jobs.append(score_job)
        
        scoring_processor = create_scoring_processor(scorer, template_name=args.template)
        score_batch_id = f"pipeline_score_{Path(args.input).stem}"
        
        scored_jobs = processor.process_batch(
            score_jobs,
            scoring_processor,
            batch_id=score_batch_id,
            resume=args.resume
        )
        
        successful_scores = [j for j in scored_jobs if j.status == 'completed']
        print(f"✅ Scoring complete: {len(successful_scores)} companies")
        
        if not successful_scores:
            print("❌ No successful scores, stopping pipeline")
            sys.exit(1)
        
        # Step 3: Clustering (optional)
        if args.cluster and len(successful_scores) >= 3:
            print("\n=== STEP 3: CLUSTERING ANALYSIS ===")
            
            clusterer = LeadClusterer(random_state=42)
            
            # Extract results for clustering
            score_results = [job.result for job in successful_scores]
            
            try:
                clusters = clusterer.cluster_leads(
                    score_results,
                    method=args.cluster_method
                )
                
                if clusters:
                    print(f"✅ Created {len(clusters)} clusters")
                    clusterer.print_cluster_summary()
                    
                    # Export cluster results
                    cluster_output = args.output.replace('.json', '_clusters.json')
                    clusterer.export_clusters(cluster_output)
                    print(f"📊 Cluster analysis saved to {cluster_output}")
                else:
                    print("⚠️  Clustering failed to generate meaningful clusters")
                    
            except Exception as e:
                logger.warning(f"Clustering failed: {e}")
                print(f"⚠️  Clustering failed: {e}")
        
        # Export final results
        processor.export_results(scored_jobs, args.output, format="json")
        
        # Generate comprehensive report
        if args.report:
            report_path = args.output.replace('.json', '_pipeline_report.md')
            processor.export_results(scored_jobs, report_path, format="report")
            print(f"📊 Pipeline report saved to {report_path}")
        
        # Clean up checkpoints
        if not args.keep_checkpoint:
            processor.checkpoint.delete_checkpoint(enrich_batch_id)
            processor.checkpoint.delete_checkpoint(score_batch_id)
        
        # Final statistics
        total_input = len(enrich_jobs)
        final_output = len(successful_scores)
        
        print(f"\n🎉 Full pipeline complete!")
        print(f"   Input: {total_input} companies")
        print(f"   Final output: {final_output} scored companies")
        print(f"   Overall success rate: {(final_output/total_input*100):.1f}%")
        print(f"   Results saved to: {args.output}")
        
        # Show top performers
        if successful_scores:
            sorted_scores = sorted(successful_scores, 
                                 key=lambda x: x.result.get('score', 0), reverse=True)
            
            print(f"\n🏆 Top 5 Companies:")
            for i, job in enumerate(sorted_scores[:5], 1):
                score = job.result.get('score', 0)
                priority = job.result.get('priority', 'N/A')
                print(f"   {i}. {job.company}: {score}/100 ({priority} Priority)")
        
    except KeyboardInterrupt:
        print(f"\n⏸️  Pipeline interrupted. Resume with --resume flag")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        print(f"❌ Pipeline failed: {e}")
        sys.exit(1)


def list_checkpoints(args):
    """List available batch checkpoints"""
    config = get_config(args.environment)
    processor = BatchProcessor(config)
    
    checkpoints = processor.checkpoint.list_checkpoints()
    
    if not checkpoints:
        print("📋 No batch checkpoints found")
        return
    
    print(f"📋 Available Batch Checkpoints:")
    print("=" * 40)
    
    for checkpoint_id in checkpoints:
        try:
            checkpoint_data = processor.checkpoint.load_checkpoint(checkpoint_id)
            if checkpoint_data:
                jobs, metadata = checkpoint_data
                
                total_jobs = len(jobs)
                completed = sum(1 for j in jobs if j.status == 'completed')
                failed = sum(1 for j in jobs if j.status == 'failed')
                pending = total_jobs - completed - failed
                
                print(f"🔖 {checkpoint_id}")
                print(f"   Total: {total_jobs} | ✅ {completed} | ❌ {failed} | ⏳ {pending}")
                print(f"   Completed: {'Yes' if metadata.get('completed') else 'No'}")
                print()
            
        except Exception as e:
            print(f"🔖 {checkpoint_id} (corrupted: {e})")


def cleanup_batch_data(args):
    """Clean up batch processing temporary data"""
    config = get_config(args.environment)
    processor = BatchProcessor(config)
    
    print("🧹 Cleaning up batch processing data...")
    
    # Clean up temp files
    processor.cleanup_temp_files(older_than_hours=args.older_than)
    
    # Clean cache if requested
    if args.clear_cache:
        processor.cache.clear()
        print("✅ Cleared all cache files")
    
    # Clean specific checkpoints if requested
    if args.checkpoint:
        processor.checkpoint.delete_checkpoint(args.checkpoint)
        print(f"✅ Deleted checkpoint: {args.checkpoint}")
    
    print("✅ Cleanup complete!")


def main():
    parser = argparse.ArgumentParser(
        description='Enhanced Batch Processing CLI for Recursor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Batch enrichment with 10 concurrent workers
  python cli_batch.py enrich --input leads.csv --output enriched.json

  # Batch scoring with custom template
  python cli_batch.py score --input enriched.json --output scored.json --template custom.txt

  # Full pipeline with clustering
  python cli_batch.py full-pipeline --input leads.csv --output results.json --cluster

  # Resume interrupted batch
  python cli_batch.py enrich --input leads.csv --output enriched.json --resume --batch-id my_batch

  # List and manage checkpoints
  python cli_batch.py list-checkpoints
  python cli_batch.py cleanup --older-than 72 --clear-cache
        """
    )
    
    # Global options
    parser.add_argument('--environment', default='development', help='Configuration environment')
    parser.add_argument('--config-dir', default='config', help='Configuration directory')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Batch enrich command
    enrich_cmd = subparsers.add_parser('enrich', help='Batch enrichment processing')
    enrich_cmd.add_argument('--input', required=True, help='Input CSV file')
    enrich_cmd.add_argument('--output', required=True, help='Output JSON file')
    enrich_cmd.add_argument('--batch-id', help='Custom batch ID for checkpointing')
    enrich_cmd.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    enrich_cmd.add_argument('--report', action='store_true', help='Generate processing report')
    enrich_cmd.add_argument('--keep-checkpoint', action='store_true', help='Keep checkpoint after completion')
    
    # Batch score command
    score_cmd = subparsers.add_parser('score', help='Batch scoring processing')
    score_cmd.add_argument('--input', required=True, help='Input JSON file (enriched data)')
    score_cmd.add_argument('--output', required=True, help='Output JSON file')
    score_cmd.add_argument('--model', choices=['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'], 
                          default='gpt-4-turbo', help='OpenAI model')
    score_cmd.add_argument('--template', default='recurly_template.txt', help='Scoring template')
    score_cmd.add_argument('--batch-id', help='Custom batch ID for checkpointing')
    score_cmd.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    score_cmd.add_argument('--report', action='store_true', help='Generate processing report')
    score_cmd.add_argument('--keep-checkpoint', action='store_true', help='Keep checkpoint after completion')
    
    # Full pipeline command
    pipeline_cmd = subparsers.add_parser('full-pipeline', help='Run complete batch pipeline')
    pipeline_cmd.add_argument('--input', required=True, help='Input CSV file')
    pipeline_cmd.add_argument('--output', required=True, help='Output JSON file')
    pipeline_cmd.add_argument('--model', choices=['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'], 
                             default='gpt-4-turbo', help='OpenAI model')
    pipeline_cmd.add_argument('--template', default='recurly_template.txt', help='Scoring template')
    pipeline_cmd.add_argument('--cluster', action='store_true', help='Include clustering analysis')
    pipeline_cmd.add_argument('--cluster-method', choices=['kmeans', 'hierarchical', 'dbscan'], 
                             default='kmeans', help='Clustering method')
    pipeline_cmd.add_argument('--resume', action='store_true', help='Resume from checkpoints')
    pipeline_cmd.add_argument('--report', action='store_true', help='Generate comprehensive report')
    pipeline_cmd.add_argument('--keep-checkpoint', action='store_true', help='Keep checkpoints after completion')
    
    # List checkpoints command
    list_cmd = subparsers.add_parser('list-checkpoints', help='List available batch checkpoints')
    
    # Cleanup command
    cleanup_cmd = subparsers.add_parser('cleanup', help='Clean up batch processing data')
    cleanup_cmd.add_argument('--older-than', type=int, default=72, help='Clean files older than N hours')
    cleanup_cmd.add_argument('--clear-cache', action='store_true', help='Clear all cache files')
    cleanup_cmd.add_argument('--checkpoint', help='Delete specific checkpoint')
    
    args = parser.parse_args()
    
    # Route commands
    if args.command == 'enrich':
        batch_enrich(args)
    elif args.command == 'score':
        batch_score(args)
    elif args.command == 'full-pipeline':
        batch_full_pipeline(args)
    elif args.command == 'list-checkpoints':
        list_checkpoints(args)
    elif args.command == 'cleanup':
        cleanup_batch_data(args)
    else:
        parser.print_help()
        print("\n❌ Error: Please specify a command")
        sys.exit(1)


if __name__ == "__main__":
    main()
