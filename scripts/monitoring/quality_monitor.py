#!/usr/bin/env python3
"""
Continuous quality monitoring for the Metal History Knowledge Graph
"""

import json
import logging
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import sys
import os

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from extraction.enhanced_extraction import extract_entities_enhanced
from scripts.automation.entity_validation import validate_entities
import kuzu


class QualityMonitor:
    """Monitor extraction and search quality over time"""
    
    def __init__(self, log_dir: str = "monitoring_logs", db_path: str = "schema/metal_history.db"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.db_path = Path(db_path)
        
        # Set up logging
        self.setup_logging()
        
        # Metrics history
        self.metrics_history = self.load_metrics_history()
        
        # Alert thresholds
        self.thresholds = {
            "extraction_f1_min": 0.7,
            "search_latency_max_ms": 100,
            "db_growth_min_percent": 0.01,
            "error_rate_max_percent": 5
        }
    
    def setup_logging(self):
        """Set up logging configuration"""
        log_file = self.log_dir / f"quality_monitor_{datetime.now():%Y%m%d}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_metrics_history(self) -> List[Dict]:
        """Load historical metrics data"""
        history_file = self.log_dir / "metrics_history.json"
        if history_file.exists():
            with open(history_file) as f:
                return json.load(f)
        return []
    
    def save_metrics_history(self):
        """Save metrics history to file"""
        history_file = self.log_dir / "metrics_history.json"
        with open(history_file, 'w') as f:
            json.dump(self.metrics_history, f, indent=2, default=str)
    
    def monitor_extraction_quality(self, test_samples: Optional[List[Dict]] = None) -> Dict:
        """Monitor extraction quality using test samples"""
        if test_samples is None:
            # Use default test samples
            test_samples = [
                {
                    "text": "Black Sabbath formed in Birmingham in 1968 with Tony Iommi on guitar.",
                    "expected_bands": ["Black Sabbath"],
                    "expected_people": ["Tony Iommi"]
                },
                {
                    "text": "Iron Maiden released their album 'The Number of the Beast' in 1982.",
                    "expected_bands": ["Iron Maiden"],
                    "expected_albums": ["The Number of the Beast"]
                }
            ]
        
        results = []
        errors = 0
        
        for sample in test_samples:
            try:
                # Extract entities
                start_time = time.time()
                extracted = extract_entities_enhanced(sample["text"])
                extraction_time = (time.time() - start_time) * 1000
                
                # Calculate accuracy
                extracted_bands = {band.name for band in extracted.bands}
                extracted_people = {person.name for person in extracted.people}
                
                expected_bands = set(sample.get("expected_bands", []))
                expected_people = set(sample.get("expected_people", []))
                
                # Simple accuracy calculation
                band_accuracy = len(extracted_bands & expected_bands) / len(expected_bands) if expected_bands else 1.0
                people_accuracy = len(extracted_people & expected_people) / len(expected_people) if expected_people else 1.0
                
                results.append({
                    "accuracy": (band_accuracy + people_accuracy) / 2,
                    "extraction_time_ms": extraction_time
                })
                
            except Exception as e:
                self.logger.error(f"Extraction error: {e}")
                errors += 1
        
        # Calculate metrics
        if results:
            avg_accuracy = statistics.mean(r["accuracy"] for r in results)
            avg_time = statistics.mean(r["extraction_time_ms"] for r in results)
            error_rate = errors / (len(results) + errors)
            
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "extraction_accuracy": avg_accuracy,
                "extraction_time_ms": avg_time,
                "error_rate": error_rate,
                "sample_count": len(results)
            }
            
            # Check thresholds and alert
            if avg_accuracy < self.thresholds["extraction_f1_min"]:
                self.alert(f"Extraction accuracy degraded: {avg_accuracy:.3f}")
            
            if error_rate > self.thresholds["error_rate_max_percent"] / 100:
                self.alert(f"High error rate: {error_rate*100:.1f}%")
            
            self.logger.info(f"Extraction Quality - Accuracy: {avg_accuracy:.3f}, "
                           f"Time: {avg_time:.1f}ms, Errors: {error_rate*100:.1f}%")
            
            return metrics
        
        return {}
    
    def monitor_search_performance(self) -> Dict:
        """Monitor vector search performance"""
        if not self.db_path.exists():
            self.logger.warning("Database not found, skipping search monitoring")
            return {}
        
        try:
            # Connect to database
            db = kuzu.Database(str(self.db_path))
            conn = kuzu.Connection(db)
            
            # Test queries
            test_queries = [
                {
                    "embedding": [0.1] * 1024,  # Mock embedding
                    "query": "British heavy metal bands"
                },
                {
                    "embedding": [0.2] * 1024,
                    "query": "Thrash metal albums 1980s"
                }
            ]
            
            latencies = []
            errors = 0
            
            for test_query in test_queries:
                try:
                    start_time = time.time()
                    
                    # Vector similarity search
                    result = conn.execute("""
                        MATCH (b:Band)
                        WHERE b.embedding IS NOT NULL
                        RETURN b.name, 
                               array_cosine_similarity(b.embedding, $query_emb) as similarity
                        ORDER BY similarity DESC
                        LIMIT 10
                    """, {"query_emb": test_query["embedding"]})
                    
                    # Consume results
                    results = []
                    while result.has_next():
                        results.append(result.get_next())
                    
                    latency = (time.time() - start_time) * 1000
                    latencies.append(latency)
                    
                except Exception as e:
                    self.logger.error(f"Search error: {e}")
                    errors += 1
            
            if latencies:
                avg_latency = statistics.mean(latencies)
                max_latency = max(latencies)
                
                metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "search_latency_ms": {
                        "mean": avg_latency,
                        "max": max_latency
                    },
                    "error_rate": errors / (len(latencies) + errors)
                }
                
                # Check thresholds
                if avg_latency > self.thresholds["search_latency_max_ms"]:
                    self.alert(f"Search latency high: {avg_latency:.1f}ms")
                
                self.logger.info(f"Search Performance - Avg Latency: {avg_latency:.1f}ms, "
                               f"Max: {max_latency:.1f}ms")
                
                return metrics
                
        except Exception as e:
            self.logger.error(f"Database connection error: {e}")
        
        return {}
    
    def monitor_database_growth(self) -> Dict:
        """Monitor database growth and entity counts"""
        if not self.db_path.exists():
            self.logger.warning("Database not found, skipping growth monitoring")
            return {}
        
        try:
            db = kuzu.Database(str(self.db_path))
            conn = kuzu.Connection(db)
            
            # Get entity counts
            entity_counts = {}
            for entity_type in ["Band", "Person", "Album", "Song", "Label", "Subgenre"]:
                try:
                    result = conn.execute(f"MATCH (n:{entity_type}) RETURN COUNT(n)")
                    count = result.get_next()[0]
                    entity_counts[entity_type.lower()] = count
                except:
                    entity_counts[entity_type.lower()] = 0
            
            # Get relationship counts
            relationship_counts = {}
            for rel_type in ["MEMBER_OF", "RELEASED", "INFLUENCED_BY", "HAS_GENRE"]:
                try:
                    result = conn.execute(f"MATCH ()-[r:{rel_type}]->() RETURN COUNT(r)")
                    count = result.get_next()[0]
                    relationship_counts[rel_type.lower()] = count
                except:
                    relationship_counts[rel_type.lower()] = 0
            
            # Calculate growth rate
            growth_rate = 0
            if self.metrics_history:
                # Find last database metrics
                last_db_metrics = None
                for metric in reversed(self.metrics_history):
                    if "entity_counts" in metric:
                        last_db_metrics = metric
                        break
                
                if last_db_metrics:
                    last_total = sum(last_db_metrics["entity_counts"].values())
                    current_total = sum(entity_counts.values())
                    if last_total > 0:
                        growth_rate = (current_total - last_total) / last_total
            
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "entity_counts": entity_counts,
                "relationship_counts": relationship_counts,
                "total_entities": sum(entity_counts.values()),
                "total_relationships": sum(relationship_counts.values()),
                "growth_rate": growth_rate
            }
            
            # Check growth threshold
            if growth_rate < self.thresholds["db_growth_min_percent"] / 100 and self.metrics_history:
                self.alert(f"Database growth stalled: {growth_rate*100:.2f}%")
            
            self.logger.info(f"Database Stats - Entities: {metrics['total_entities']}, "
                           f"Relationships: {metrics['total_relationships']}, "
                           f"Growth: {growth_rate*100:.2f}%")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Database monitoring error: {e}")
        
        return {}
    
    def monitor_data_quality(self, sample_file: Optional[str] = None) -> Dict:
        """Monitor data quality metrics"""
        if sample_file is None:
            # Use most recent extracted entities file
            sample_file = "extracted_entities.json"
        
        if not Path(sample_file).exists():
            self.logger.warning(f"Sample file {sample_file} not found")
            return {}
        
        try:
            # Validate entities
            validation_report = validate_entities(sample_file)
            
            # Extract key metrics
            total_entities = validation_report["summary"]["total_entities"]
            quality_issues = []
            
            for entity_type, stats in validation_report["summary"].items():
                if isinstance(stats, dict) and "quality_issues" in stats:
                    quality_issues.extend(stats["quality_issues"])
            
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "total_entities": total_entities,
                "quality_issue_count": len(quality_issues),
                "completeness_scores": {},
                "validation_passed": validation_report.get("validation_passed", True)
            }
            
            # Calculate completeness scores
            for entity_type in ["bands", "people", "albums"]:
                if entity_type in validation_report["summary"]:
                    stats = validation_report["summary"][entity_type]
                    if "missing_fields" in stats:
                        total_fields = stats.get("total_fields", 1)
                        missing = len(stats["missing_fields"])
                        completeness = 1 - (missing / total_fields) if total_fields > 0 else 1
                        metrics["completeness_scores"][entity_type] = completeness
            
            self.logger.info(f"Data Quality - Entities: {total_entities}, "
                           f"Issues: {len(quality_issues)}")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Data quality monitoring error: {e}")
        
        return {}
    
    def alert(self, message: str):
        """Send an alert (currently just logs, could be extended)"""
        self.logger.warning(f"ALERT: {message}")
        
        # In production, this could:
        # - Send email
        # - Post to Slack
        # - Create GitHub issue
        # - Trigger PagerDuty
    
    def run_all_monitors(self) -> Dict:
        """Run all monitoring checks"""
        self.logger.info("Running all quality monitors...")
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "monitors": {}
        }
        
        # Run each monitor
        monitors = [
            ("extraction_quality", self.monitor_extraction_quality),
            ("search_performance", self.monitor_search_performance),
            ("database_growth", self.monitor_database_growth),
            ("data_quality", self.monitor_data_quality)
        ]
        
        for name, monitor_func in monitors:
            try:
                result = monitor_func()
                metrics["monitors"][name] = result
            except Exception as e:
                self.logger.error(f"Monitor {name} failed: {e}")
                metrics["monitors"][name] = {"error": str(e)}
        
        # Save to history
        self.metrics_history.append(metrics)
        self.save_metrics_history()
        
        # Generate summary
        self.generate_summary_report(metrics)
        
        return metrics
    
    def generate_summary_report(self, metrics: Dict):
        """Generate a summary report of current status"""
        report_file = self.log_dir / f"quality_report_{datetime.now():%Y%m%d_%H%M%S}.json"
        
        summary = {
            "timestamp": metrics["timestamp"],
            "status": "healthy",  # Will be updated based on checks
            "issues": [],
            "metrics": {}
        }
        
        # Check each monitor's results
        for monitor_name, monitor_data in metrics["monitors"].items():
            if "error" in monitor_data:
                summary["status"] = "error"
                summary["issues"].append(f"{monitor_name}: {monitor_data['error']}")
            elif monitor_data:
                # Extract key metrics
                if monitor_name == "extraction_quality":
                    summary["metrics"]["extraction_accuracy"] = monitor_data.get("extraction_accuracy", 0)
                elif monitor_name == "search_performance":
                    summary["metrics"]["search_latency_ms"] = monitor_data.get("search_latency_ms", {}).get("mean", 0)
                elif monitor_name == "database_growth":
                    summary["metrics"]["total_entities"] = monitor_data.get("total_entities", 0)
                    summary["metrics"]["growth_rate"] = monitor_data.get("growth_rate", 0)
        
        # Determine overall status
        if summary["issues"]:
            summary["status"] = "unhealthy" if len(summary["issues"]) > 1 else "degraded"
        
        # Save report
        with open(report_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info(f"Summary report saved to {report_file}")
        self.logger.info(f"System Status: {summary['status'].upper()}")


def main():
    """Run the quality monitor"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor Metal History Knowledge Graph quality")
    parser.add_argument("--continuous", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=3600, help="Check interval in seconds (default: 3600)")
    parser.add_argument("--log-dir", default="monitoring_logs", help="Directory for logs")
    
    args = parser.parse_args()
    
    monitor = QualityMonitor(log_dir=args.log_dir)
    
    if args.continuous:
        print(f"Starting continuous monitoring (interval: {args.interval}s)...")
        while True:
            try:
                monitor.run_all_monitors()
                time.sleep(args.interval)
            except KeyboardInterrupt:
                print("\nMonitoring stopped.")
                break
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait a minute before retrying
    else:
        # Run once
        monitor.run_all_monitors()


if __name__ == "__main__":
    main()