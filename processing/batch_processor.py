#!/usr/bin/env python3
"""
Advanced Batch Processing System for Recursor
Supports concurrent processing, caching, checkpoints, and resumption
"""

import asyncio
import json
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Tuple, Iterator
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from datetime import datetime, timedelta
import pickle
import logging

# Import configuration
import sys
sys.path.append(str(Path(__file__).parent.parent))
from config.config_manager import get_config, RecursorConfig


@dataclass
class BatchJob:
    """Represents a single job in a batch"""
    id: str
    company: str
    domain: Optional[str] = None
    status: str = "pending"  # pending, processing, completed, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    attempts: int = 0
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now()
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate unique job ID"""
        content = f"{self.company}_{self.domain}_{self.created_at.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def mark_processing(self):
        """Mark job as processing"""
        self.status = "processing"
        self.started_at = datetime.now()
        self.attempts += 1
    
    def mark_completed(self, result: Dict[str, Any]):
        """Mark job as completed with result"""
        self.status = "completed"
        self.result = result
        self.completed_at = datetime.now()
    
    def mark_failed(self, error: str):
        """Mark job as failed with error"""
        self.status = "failed"
        self.error = error
        self.completed_at = datetime.now()
    
    @property
    def processing_time(self) -> Optional[float]:
        """Get processing time in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class BatchCache:
    """Simple file-based cache for batch processing results"""
    
    def __init__(self, cache_dir: str, ttl_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = ttl_hours
    
    def _cache_key(self, company: str, domain: str = "", step: str = "enrichment") -> str:
        """Generate cache key"""
        content = f"{step}_{company}_{domain}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _cache_path(self, cache_key: str) -> Path:
        """Get cache file path"""
        return self.cache_dir / f"{cache_key}.cache"
    
    def get(self, company: str, domain: str = "", step: str = "enrichment") -> Optional[Dict[str, Any]]:
        """Get cached result"""
        cache_key = self._cache_key(company, domain, step)
        cache_path = self._cache_path(cache_key)
        
        if not cache_path.exists():
            return None
        
        # Check TTL
        cache_age = time.time() - cache_path.stat().st_mtime
        if cache_age > (self.ttl_hours * 3600):
            cache_path.unlink()  # Delete expired cache
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            # Delete corrupted cache
            cache_path.unlink()
            return None
    
    def set(self, company: str, result: Dict[str, Any], domain: str = "", step: str = "enrichment"):
        """Set cache result"""
        cache_key = self._cache_key(company, domain, step)
        cache_path = self._cache_path(cache_key)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(result, f)
        except Exception as e:
            logging.warning(f"Failed to cache result for {company}: {e}")
    
    def clear(self):
        """Clear all cache files"""
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()
    
    def cleanup_expired(self):
        """Remove expired cache files"""
        current_time = time.time()
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_age = current_time - cache_file.stat().st_mtime
            if cache_age > (self.ttl_hours * 3600):
                cache_file.unlink()


class BatchCheckpoint:
    """Checkpoint system for batch processing resumption"""
    
    def __init__(self, checkpoint_dir: str):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def save_checkpoint(self, batch_id: str, jobs: List[BatchJob], metadata: Dict[str, Any]):
        """Save batch checkpoint"""
        checkpoint_data = {
            'batch_id': batch_id,
            'jobs': [asdict(job) for job in jobs],
            'metadata': metadata,
            'timestamp': datetime.now().isoformat(),
        }
        
        checkpoint_path = self.checkpoint_dir / f"{batch_id}.checkpoint"
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2, default=str)
    
    def load_checkpoint(self, batch_id: str) -> Optional[Tuple[List[BatchJob], Dict[str, Any]]]:
        """Load batch checkpoint"""
        checkpoint_path = self.checkpoint_dir / f"{batch_id}.checkpoint"
        
        if not checkpoint_path.exists():
            return None
        
        try:
            with open(checkpoint_path, 'r') as f:
                data = json.load(f)
            
            # Convert back to BatchJob objects
            jobs = []
            for job_data in data['jobs']:
                job = BatchJob(**job_data)
                # Convert datetime strings back to objects
                if isinstance(job.created_at, str):
                    job.created_at = datetime.fromisoformat(job.created_at)
                if job.started_at and isinstance(job.started_at, str):
                    job.started_at = datetime.fromisoformat(job.started_at)
                if job.completed_at and isinstance(job.completed_at, str):
                    job.completed_at = datetime.fromisoformat(job.completed_at)
                jobs.append(job)
            
            return jobs, data.get('metadata', {})
        
        except Exception as e:
            logging.error(f"Failed to load checkpoint {batch_id}: {e}")
            return None
    
    def delete_checkpoint(self, batch_id: str):
        """Delete checkpoint file"""
        checkpoint_path = self.checkpoint_dir / f"{batch_id}.checkpoint"
        if checkpoint_path.exists():
            checkpoint_path.unlink()
    
    def list_checkpoints(self) -> List[str]:
        """List available checkpoints"""
        return [f.stem for f in self.checkpoint_dir.glob("*.checkpoint")]


class ProgressTracker:
    """Progress tracking for batch operations"""
    
    def __init__(self, total_jobs: int, update_interval: int = 1):
        self.total_jobs = total_jobs
        self.completed_jobs = 0
        self.failed_jobs = 0
        self.update_interval = update_interval
        self.start_time = time.time()
        self.last_update = 0
        self.lock = threading.Lock()
    
    def update(self, completed: int = 0, failed: int = 0):
        """Update progress counters"""
        with self.lock:
            self.completed_jobs += completed
            self.failed_jobs += failed
            
            current_time = time.time()
            if current_time - self.last_update >= self.update_interval:
                self._print_progress()
                self.last_update = current_time
    
    def _print_progress(self):
        """Print current progress"""
        total_processed = self.completed_jobs + self.failed_jobs
        percentage = (total_processed / self.total_jobs) * 100
        elapsed = time.time() - self.start_time
        
        if total_processed > 0:
            avg_time_per_job = elapsed / total_processed
            remaining_jobs = self.total_jobs - total_processed
            eta_seconds = remaining_jobs * avg_time_per_job
            eta_str = str(timedelta(seconds=int(eta_seconds)))
        else:
            eta_str = "Unknown"
        
        print(f"\r🔄 Progress: {total_processed}/{self.total_jobs} ({percentage:.1f}%) "
              f"✅ {self.completed_jobs} ❌ {self.failed_jobs} ETA: {eta_str}", end='')
    
    def finish(self):
        """Print final progress"""
        self._print_progress()
        total_time = time.time() - self.start_time
        print(f"\n⏱️  Total time: {str(timedelta(seconds=int(total_time)))}")
        print(f"📊 Success rate: {(self.completed_jobs / self.total_jobs) * 100:.1f}%")


class BatchProcessor:
    """Advanced batch processing engine"""
    
    def __init__(self, config: Optional[RecursorConfig] = None):
        self.config = config or get_config()
        self.cache = BatchCache(
            cache_dir=Path(self.config.processing.temp_directory) / "cache",
            ttl_hours=self.config.processing.cache_ttl_hours
        )
        self.checkpoint = BatchCheckpoint(
            checkpoint_dir=Path(self.config.processing.temp_directory) / "checkpoints"
        )
        self.logger = self.config.setup_logging()
    
    def process_batch(
        self,
        jobs: List[BatchJob],
        processor_func: Callable[[BatchJob], Dict[str, Any]],
        batch_id: str = None,
        resume: bool = None
    ) -> List[BatchJob]:
        """Process batch of jobs with concurrent execution"""
        
        if not batch_id:
            batch_id = f"batch_{int(time.time())}"
        
        if resume is None:
            resume = self.config.processing.enable_resume
        
        # Try to resume from checkpoint
        if resume:
            checkpoint_data = self.checkpoint.load_checkpoint(batch_id)
            if checkpoint_data:
                jobs, metadata = checkpoint_data
                self.logger.info(f"Resuming batch {batch_id} with {len(jobs)} jobs")
                
                # Filter out completed jobs
                pending_jobs = [j for j in jobs if j.status in ['pending', 'failed']]
                self.logger.info(f"Found {len(pending_jobs)} jobs to process")
                jobs = pending_jobs
        
        if not jobs:
            self.logger.info("No jobs to process")
            return []
        
        # Setup progress tracking
        progress = ProgressTracker(
            total_jobs=len(jobs),
            update_interval=self.config.processing.progress_update_interval
        )
        
        # Process with thread pool
        max_workers = min(
            self.config.processing.max_concurrent_requests,
            len(jobs)
        )
        
        self.logger.info(f"Processing {len(jobs)} jobs with {max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all jobs
            future_to_job = {
                executor.submit(self._process_single_job, job, processor_func): job
                for job in jobs
            }
            
            processed_count = 0
            
            # Process completed jobs
            for future in as_completed(future_to_job):
                job = future_to_job[future]
                
                try:
                    result = future.result()
                    if result:
                        job.mark_completed(result)
                        progress.update(completed=1)
                    else:
                        job.mark_failed("No result returned")
                        progress.update(failed=1)
                
                except Exception as e:
                    job.mark_failed(str(e))
                    progress.update(failed=1)
                    self.logger.error(f"Job {job.id} failed: {e}")
                
                processed_count += 1
                
                # Save checkpoint periodically
                if (processed_count % self.config.processing.checkpoint_interval == 0 
                    and self.config.processing.enable_resume):
                    self.checkpoint.save_checkpoint(batch_id, jobs, {'processed': processed_count})
        
        progress.finish()
        
        # Final checkpoint
        if self.config.processing.enable_resume:
            self.checkpoint.save_checkpoint(batch_id, jobs, {'completed': True})
        
        # Statistics
        completed = sum(1 for j in jobs if j.status == 'completed')
        failed = sum(1 for j in jobs if j.status == 'failed')
        
        self.logger.info(f"Batch processing complete: {completed} succeeded, {failed} failed")
        
        return jobs
    
    def _process_single_job(self, job: BatchJob, processor_func: Callable) -> Optional[Dict[str, Any]]:
        """Process a single job with caching and retry logic"""
        job.mark_processing()
        
        # Check cache if enabled
        if self.config.processing.enable_caching:
            cached_result = self.cache.get(job.company, job.domain or "")
            if cached_result:
                self.logger.debug(f"Using cached result for {job.company}")
                return cached_result
        
        max_retries = self.config.api.max_retries
        retry_delay = self.config.api.retry_delay
        
        for attempt in range(max_retries + 1):
            try:
                result = processor_func(job)
                
                # Cache result if enabled
                if self.config.processing.enable_caching and result:
                    self.cache.set(job.company, result, job.domain or "")
                
                return result
            
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {job.company}: {e}")
                
                if attempt < max_retries:
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    self.logger.error(f"All attempts failed for {job.company}")
                    raise e
        
        return None
    
    def create_jobs_from_csv(self, csv_path: str) -> List[BatchJob]:
        """Create batch jobs from CSV file"""
        import pandas as pd
        
        df = pd.read_csv(csv_path)
        jobs = []
        
        for _, row in df.iterrows():
            job = BatchJob(
                company=row.get('company', ''),
                domain=row.get('domain', ''),
                id=None  # Will be auto-generated
            )
            jobs.append(job)
        
        self.logger.info(f"Created {len(jobs)} jobs from {csv_path}")
        return jobs
    
    def export_results(self, jobs: List[BatchJob], output_path: str, format: str = "json"):
        """Export batch processing results"""
        completed_jobs = [j for j in jobs if j.status == 'completed' and j.result]
        
        if format.lower() == "json":
            results = [job.result for job in completed_jobs]
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
        
        elif format.lower() == "csv":
            import pandas as pd
            
            # Flatten results for CSV
            flattened_results = []
            for job in completed_jobs:
                flat_result = {'company': job.company, 'domain': job.domain}
                flat_result.update(job.result)
                flattened_results.append(flat_result)
            
            df = pd.DataFrame(flattened_results)
            df.to_csv(output_path, index=False)
        
        elif format.lower() == "report":
            # Generate processing report
            self._generate_processing_report(jobs, output_path)
        
        self.logger.info(f"Exported {len(completed_jobs)} results to {output_path}")
    
    def _generate_processing_report(self, jobs: List[BatchJob], output_path: str):
        """Generate detailed processing report"""
        completed = [j for j in jobs if j.status == 'completed']
        failed = [j for j in jobs if j.status == 'failed']
        
        # Calculate statistics
        total_time = sum(j.processing_time or 0 for j in completed)
        avg_time = total_time / len(completed) if completed else 0
        
        report = f"""
# Batch Processing Report
Generated: {datetime.now().isoformat()}

## Summary
- Total Jobs: {len(jobs)}
- Completed: {len(completed)} ({len(completed)/len(jobs)*100:.1f}%)
- Failed: {len(failed)} ({len(failed)/len(jobs)*100:.1f}%)
- Average Processing Time: {avg_time:.2f} seconds

## Performance Metrics
- Total Processing Time: {total_time:.2f} seconds
- Fastest Job: {min(j.processing_time or 0 for j in completed):.2f}s
- Slowest Job: {max(j.processing_time or 0 for j in completed):.2f}s

## Failed Jobs
"""
        for job in failed[:10]:  # Show first 10 failures
            report += f"- {job.company}: {job.error}\n"
        
        if len(failed) > 10:
            report += f"... and {len(failed) - 10} more failures\n"
        
        with open(output_path, 'w') as f:
            f.write(report)
    
    def cleanup_temp_files(self, older_than_hours: int = 72):
        """Clean up old temporary files"""
        cutoff_time = time.time() - (older_than_hours * 3600)
        
        # Clean cache
        self.cache.cleanup_expired()
        
        # Clean old checkpoints
        for checkpoint_file in self.checkpoint.checkpoint_dir.glob("*.checkpoint"):
            if checkpoint_file.stat().st_mtime < cutoff_time:
                checkpoint_file.unlink()
                self.logger.info(f"Deleted old checkpoint: {checkpoint_file.name}")


# Convenience functions for common operations
def create_enrichment_processor(enricher):
    """Create processor function for enrichment"""
    def process_job(job: BatchJob) -> Dict[str, Any]:
        return enricher.enrich_company(job.company)
    return process_job

def create_scoring_processor(scorer, template_name: str = None):
    """Create processor function for scoring"""
    def process_job(job: BatchJob) -> Dict[str, Any]:
        # Assume job.result contains enrichment data
        if job.result:
            return scorer.score_lead(job.result, template_name=template_name)
        else:
            raise ValueError("No enrichment data available for scoring")
    return process_job


if __name__ == "__main__":
    # Demo usage
    from config.config_manager import ConfigManager
    
    config_manager = ConfigManager()
    config = config_manager.load_config("development")
    
    processor = BatchProcessor(config)
    
    # Create sample jobs
    jobs = [
        BatchJob(company="Shopify", domain="shopify.com"),
        BatchJob(company="Zoom", domain="zoom.us"),
        BatchJob(company="Netflix", domain="netflix.com")
    ]
    
    # Dummy processor function
    def dummy_processor(job: BatchJob) -> Dict[str, Any]:
        time.sleep(1)  # Simulate processing
        return {"company": job.company, "processed": True}
    
    print("Starting batch processing demo...")
    results = processor.process_batch(jobs, dummy_processor)
    
    print(f"Processed {len(results)} jobs")
    for job in results:
        print(f"- {job.company}: {job.status}")
