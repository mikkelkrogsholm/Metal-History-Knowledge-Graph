#!/usr/bin/env python3
"""
Enhanced extraction pipeline with specialized entity extraction
Supports all entity types from the enhanced schema
"""

import json
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.extraction.enhanced_extraction_specialized import SpecializedExtractor
from src.extraction.confidence_scorer import ConfidenceScorer
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedExtractionPipeline:
    """Pipeline for enhanced entity extraction with all entity types"""
    
    def __init__(self, model: str = 'magistral:24b'):
        self.extractor = SpecializedExtractor(model=model)
        self.confidence_scorer = ConfidenceScorer()
        
    def load_chunks(self, chunks_path: str) -> List[Dict[str, Any]]:
        """Load text chunks from JSON file"""
        with open(chunks_path, 'r') as f:
            data = json.load(f)
        
        # Handle both formats (with/without metadata wrapper)
        if 'chunks' in data:
            chunks = data['chunks']
        else:
            chunks = data
        
        logger.info(f"Loaded {len(chunks)} chunks from {chunks_path}")
        return chunks
    
    def save_results(self, results: Dict[str, Any], output_path: str):
        """Save extraction results to JSON file"""
        # Add timestamp and version info
        results['metadata']['extraction_timestamp'] = datetime.now().isoformat()
        results['metadata']['pipeline_version'] = '2.0-enhanced'
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Saved results to {output_path}")
    
    def generate_extraction_report(self, results: Dict[str, Any]) -> str:
        """Generate a detailed extraction report"""
        report_lines = [
            "# Enhanced Extraction Report",
            f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Pipeline Version: 2.0-enhanced",
            "\n## Entity Counts"
        ]
        
        # Entity counts
        total_entities = 0
        for entity_type, entities in results['entities'].items():
            count = len(entities)
            total_entities += count
            if count > 0:
                report_lines.append(f"- {entity_type.replace('_', ' ').title()}: {count}")
        
        report_lines.append(f"\n**Total Entities**: {total_entities}")
        
        # Confidence analysis
        confidence_report = results['metadata']['confidence_report']
        report_lines.extend([
            "\n## Confidence Analysis",
            f"- Overall Confidence: {confidence_report['overall_confidence']:.2%}",
            f"- High Confidence Entities: {confidence_report['high_confidence_count']}",
            f"- Medium Confidence Entities: {confidence_report['medium_confidence_count']}",
            f"- Low Confidence Entities: {confidence_report['low_confidence_count']}"
        ])
        
        # Entity type breakdown
        report_lines.append("\n### Confidence by Entity Type")
        for entity_type, stats in confidence_report['entity_type_confidence'].items():
            report_lines.append(
                f"- {entity_type}: avg={stats['average']:.2f}, "
                f"min={stats['min']:.2f}, max={stats['max']:.2f} "
                f"(n={stats['count']})"
            )
        
        # New entity types extracted
        new_types = ['movements', 'equipment', 'production_styles', 'venues', 
                    'platforms', 'technical_details', 'academic_resources',
                    'compilations', 'viral_phenomena', 'web3_projects']
        
        report_lines.append("\n## Enhanced Entity Extraction")
        for entity_type in new_types:
            entities = results['entities'].get(entity_type, [])
            if entities:
                report_lines.append(f"\n### {entity_type.replace('_', ' ').title()}")
                # Show top 5 by confidence
                sorted_entities = sorted(
                    entities, 
                    key=lambda x: getattr(x, 'confidence', 0.5) if hasattr(x, 'confidence') else 0.5,
                    reverse=True
                )[:5]
                
                for entity in sorted_entities:
                    name = getattr(entity, 'name', getattr(entity, 'title', str(entity)))
                    conf = getattr(entity, 'confidence', 0.5) if hasattr(entity, 'confidence') else 0.5
                    report_lines.append(f"  - {name} (confidence: {conf:.2f})")
        
        # Processing statistics
        report_lines.extend([
            "\n## Processing Statistics",
            f"- Chunks Processed: {results['metadata']['chunks_processed']}",
            f"- Extraction Method: {results['metadata']['extraction_method']}",
        ])
        
        # Chunk-level analysis
        if 'chunk_scores' in results['metadata']:
            chunk_scores = results['metadata']['chunk_scores']
            avg_chunk_score = sum(cs['overall'] for cs in chunk_scores) / len(chunk_scores)
            report_lines.append(f"- Average Chunk Confidence: {avg_chunk_score:.2%}")
        
        return "\n".join(report_lines)
    
    def run(self, chunks_path: str, output_path: str, limit: Optional[int] = None,
            use_specialized: bool = True, generate_report: bool = True):
        """
        Run the enhanced extraction pipeline
        
        Args:
            chunks_path: Path to chunks JSON file
            output_path: Path to save extraction results
            limit: Maximum number of chunks to process
            use_specialized: Whether to use specialized extraction
            generate_report: Whether to generate a report
        """
        logger.info("Starting enhanced extraction pipeline...")
        
        # Load chunks
        chunks = self.load_chunks(chunks_path)
        
        # Extract entities
        results = self.extractor.extract_from_chunks(
            chunks, 
            limit=limit,
            use_specialized=use_specialized
        )
        
        # Convert entity objects to dictionaries for JSON serialization
        serialized_results = {
            'entities': {},
            'metadata': results['metadata']
        }
        
        for entity_type, entities in results['entities'].items():
            serialized_results['entities'][entity_type] = [
                entity.model_dump() if hasattr(entity, 'model_dump') else entity.__dict__
                for entity in entities
            ]
        
        # Save results
        self.save_results(serialized_results, output_path)
        
        # Generate and save report
        if generate_report:
            report = self.generate_extraction_report(results)
            report_path = output_path.replace('.json', '_report.md')
            with open(report_path, 'w') as f:
                f.write(report)
            logger.info(f"Saved extraction report to {report_path}")
            
            # Print summary
            print(f"\n{report}")
        
        return serialized_results


def main():
    parser = argparse.ArgumentParser(
        description="Enhanced entity extraction pipeline for metal history"
    )
    parser.add_argument(
        '--chunks',
        default='../history/chunks_optimized.json',
        help='Path to chunks JSON file'
    )
    parser.add_argument(
        '--output',
        default='enhanced_extracted_entities.json',
        help='Output path for extracted entities'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of chunks to process'
    )
    parser.add_argument(
        '--model',
        default='magistral:24b',
        help='Ollama model to use'
    )
    parser.add_argument(
        '--no-specialized',
        action='store_true',
        help='Disable specialized extraction (use basic method)'
    )
    parser.add_argument(
        '--no-report',
        action='store_true',
        help='Skip report generation'
    )
    
    args = parser.parse_args()
    
    # Create pipeline
    pipeline = EnhancedExtractionPipeline(model=args.model)
    
    # Run extraction
    pipeline.run(
        chunks_path=args.chunks,
        output_path=args.output,
        limit=args.limit,
        use_specialized=not args.no_specialized,
        generate_report=not args.no_report
    )


if __name__ == "__main__":
    main()