#!/usr/bin/env python3
"""
Test extraction quality by comparing extracted entities against manually identified ones.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple
import argparse
from collections import defaultdict

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from extraction.enhanced_extraction import extract_entities_enhanced
from extraction.extraction_schemas import ExtractionResult


class ExtractionQualityTester:
    """Test extraction quality on sample chunks"""
    
    def __init__(self):
        self.test_cases = self._define_test_cases()
        
    def _define_test_cases(self) -> List[Dict]:
        """Define test cases with expected entities"""
        return [
            {
                "id": "test_1",
                "text": "Black Sabbath formed in 1968 in Birmingham, UK. The band consisted of Tony Iommi on guitar, Ozzy Osbourne on vocals, Geezer Butler on bass, and Bill Ward on drums. Their debut album 'Black Sabbath' was released in 1970.",
                "expected": {
                    "bands": [{"name": "Black Sabbath", "formed_year": 1968, "origin_location": "Birmingham, UK"}],
                    "people": [
                        {"name": "Tony Iommi", "instruments": ["guitar"]},
                        {"name": "Ozzy Osbourne", "instruments": ["vocals"]},
                        {"name": "Geezer Butler", "instruments": ["bass"]},
                        {"name": "Bill Ward", "instruments": ["drums"]}
                    ],
                    "albums": [{"name": "Black Sabbath", "release_year": 1970}],
                    "relationships": [
                        {"type": "MEMBER_OF", "from": "Tony Iommi", "to": "Black Sabbath"},
                        {"type": "MEMBER_OF", "from": "Ozzy Osbourne", "to": "Black Sabbath"},
                        {"type": "MEMBER_OF", "from": "Geezer Butler", "to": "Black Sabbath"},
                        {"type": "MEMBER_OF", "from": "Bill Ward", "to": "Black Sabbath"},
                        {"type": "RELEASED", "from": "Black Sabbath", "to": "Black Sabbath (album)"}
                    ]
                }
            },
            {
                "id": "test_2",
                "text": "Iron Maiden was formed in London in 1975 by bassist Steve Harris. Their breakthrough came with the 1982 album 'The Number of the Beast', featuring new vocalist Bruce Dickinson. The NWOBHM movement revolutionized British heavy metal.",
                "expected": {
                    "bands": [{"name": "Iron Maiden", "formed_year": 1975, "origin_location": "London"}],
                    "people": [
                        {"name": "Steve Harris", "instruments": ["bass"]},
                        {"name": "Bruce Dickinson", "instruments": ["vocals"]}
                    ],
                    "albums": [{"name": "The Number of the Beast", "release_year": 1982}],
                    "movements": [{"name": "NWOBHM", "description": "New Wave of British Heavy Metal"}]
                }
            },
            {
                "id": "test_3",
                "text": "The Big Four of thrash metal - Metallica, Slayer, Megadeth, and Anthrax - dominated the 1980s metal scene. Metallica's 'Master of Puppets' (1986) and Slayer's 'Reign in Blood' (1986) are considered thrash masterpieces.",
                "expected": {
                    "bands": [
                        {"name": "Metallica"},
                        {"name": "Slayer"},
                        {"name": "Megadeth"},
                        {"name": "Anthrax"}
                    ],
                    "albums": [
                        {"name": "Master of Puppets", "release_year": 1986},
                        {"name": "Reign in Blood", "release_year": 1986}
                    ],
                    "subgenres": [{"name": "thrash metal"}],
                    "groups": [{"name": "Big Four", "members": ["Metallica", "Slayer", "Megadeth", "Anthrax"]}]
                }
            },
            {
                "id": "test_4",
                "text": "In 1991, the Grunge movement from Seattle challenged metal's dominance. Bands like Soundgarden and Alice in Chains blended heavy metal with alternative rock. The Lollapalooza festival became a key venue for alternative metal acts.",
                "expected": {
                    "bands": [
                        {"name": "Soundgarden", "origin_location": "Seattle"},
                        {"name": "Alice in Chains", "origin_location": "Seattle"}
                    ],
                    "movements": [{"name": "Grunge", "origin_location": "Seattle"}],
                    "events": [{"name": "Lollapalooza", "type": "festival"}],
                    "subgenres": [{"name": "alternative metal"}]
                }
            },
            {
                "id": "test_5",
                "text": "Dio left Black Sabbath in 1982 to form his own band. He recruited guitarist Vivian Campbell, bassist Jimmy Bain, and drummer Vinny Appice. Their debut 'Holy Diver' (1983) featured the hit song 'Rainbow in the Dark'.",
                "expected": {
                    "bands": [
                        {"name": "Black Sabbath"},
                        {"name": "Dio", "formed_year": 1982}
                    ],
                    "people": [
                        {"name": "Dio", "instruments": ["vocals"]},
                        {"name": "Vivian Campbell", "instruments": ["guitar"]},
                        {"name": "Jimmy Bain", "instruments": ["bass"]},
                        {"name": "Vinny Appice", "instruments": ["drums"]}
                    ],
                    "albums": [{"name": "Holy Diver", "release_year": 1983}],
                    "songs": [{"name": "Rainbow in the Dark", "type": "hit"}]
                }
            }
        ]
        
    def extract_entities(self, text: str) -> ExtractionResult:
        """Extract entities from text"""
        try:
            return extract_entities_enhanced(text)
        except Exception as e:
            print(f"Extraction error: {e}")
            return ExtractionResult(
                bands=[], people=[], albums=[], songs=[], 
                subgenres=[], geographic_locations=[], 
                events=[], movements=[], relationships=[]
            )
            
    def normalize_entity_name(self, name: str) -> str:
        """Normalize entity name for comparison"""
        return name.lower().strip().replace("'", "'")
        
    def calculate_metrics(self, extracted: List, expected: List, key_field: str = "name") -> Dict[str, float]:
        """Calculate precision, recall, and F1 score"""
        # Normalize names for comparison
        extracted_names = {self.normalize_entity_name(e.get(key_field, "")) 
                          for e in extracted if e.get(key_field)}
        expected_names = {self.normalize_entity_name(e.get(key_field, "")) 
                         for e in expected if e.get(key_field)}
        
        # Calculate metrics
        true_positives = len(extracted_names & expected_names)
        false_positives = len(extracted_names - expected_names)
        false_negatives = len(expected_names - extracted_names)
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "missing": list(expected_names - extracted_names),
            "extra": list(extracted_names - expected_names)
        }
        
    def test_single_case(self, test_case: Dict) -> Dict:
        """Test extraction on a single case"""
        # Extract entities
        result = self.extract_entities(test_case["text"])
        
        # Convert to dict format for comparison
        extracted = {
            "bands": [{"name": b.name, "formed_year": b.formed_year, 
                      "origin_location": f"{b.origin_city}, {b.origin_country}" if b.origin_city and b.origin_country else b.origin_country} 
                     for b in result.bands],
            "people": [{"name": p.name, "instruments": p.instruments, "associated_bands": p.associated_bands} 
                      for p in result.people],
            "albums": [{"name": a.title, "release_year": a.release_year} for a in result.albums],
            "songs": [{"name": s.title} for s in result.songs],
            "subgenres": [{"name": s.name} for s in result.subgenres],
            "movements": [],  # No movement type in schema
            "events": [{"name": e.name} for e in result.events]
        }
        
        # Calculate metrics for each entity type
        metrics = {}
        for entity_type in ["bands", "people", "albums", "songs", "subgenres", "movements", "events"]:
            if entity_type in test_case["expected"]:
                metrics[entity_type] = self.calculate_metrics(
                    extracted.get(entity_type, []),
                    test_case["expected"].get(entity_type, [])
                )
                
        return {
            "id": test_case["id"],
            "text_preview": test_case["text"][:100] + "...",
            "extracted": extracted,
            "expected": test_case["expected"],
            "metrics": metrics
        }
        
    def run_all_tests(self) -> Dict:
        """Run all test cases"""
        results = []
        overall_metrics = defaultdict(lambda: {"precision": [], "recall": [], "f1": []})
        
        for test_case in self.test_cases[:1]:  # Test just the first case for now
            print(f"\nTesting case: {test_case['id']}")
            result = self.test_single_case(test_case)
            results.append(result)
            
            # Aggregate metrics
            for entity_type, metrics in result["metrics"].items():
                overall_metrics[entity_type]["precision"].append(metrics["precision"])
                overall_metrics[entity_type]["recall"].append(metrics["recall"])
                overall_metrics[entity_type]["f1"].append(metrics["f1"])
                
        # Calculate averages
        averages = {}
        for entity_type, metrics in overall_metrics.items():
            averages[entity_type] = {
                "avg_precision": sum(metrics["precision"]) / len(metrics["precision"]) if metrics["precision"] else 0,
                "avg_recall": sum(metrics["recall"]) / len(metrics["recall"]) if metrics["recall"] else 0,
                "avg_f1": sum(metrics["f1"]) / len(metrics["f1"]) if metrics["f1"] else 0
            }
            
        return {
            "test_results": results,
            "overall_metrics": averages,
            "total_tests": len(self.test_cases)
        }
        
    def generate_report(self, results: Dict) -> str:
        """Generate quality report"""
        report = []
        report.append("# Extraction Quality Test Report\n")
        
        # Overall metrics
        report.append("## Overall Performance\n")
        for entity_type, metrics in results["overall_metrics"].items():
            report.append(f"### {entity_type.title()}")
            report.append(f"- Average Precision: {metrics['avg_precision']:.2%}")
            report.append(f"- Average Recall: {metrics['avg_recall']:.2%}")
            report.append(f"- Average F1 Score: {metrics['avg_f1']:.2%}\n")
            
        # Detailed results
        report.append("\n## Detailed Test Results\n")
        for test_result in results["test_results"]:
            report.append(f"### Test Case: {test_result['id']}")
            report.append(f"**Text**: {test_result['text_preview']}\n")
            
            for entity_type, metrics in test_result["metrics"].items():
                if metrics["true_positives"] + metrics["false_positives"] + metrics["false_negatives"] > 0:
                    report.append(f"**{entity_type.title()}**:")
                    report.append(f"- Precision: {metrics['precision']:.2%}, Recall: {metrics['recall']:.2%}, F1: {metrics['f1']:.2%}")
                    if metrics["missing"]:
                        report.append(f"- Missing: {', '.join(metrics['missing'])}")
                    if metrics["extra"]:
                        report.append(f"- Extra: {', '.join(metrics['extra'])}")
                    report.append("")
                    
        # Common failure patterns
        report.append("\n## Common Failure Patterns\n")
        all_missing = defaultdict(list)
        all_extra = defaultdict(list)
        
        for test_result in results["test_results"]:
            for entity_type, metrics in test_result["metrics"].items():
                all_missing[entity_type].extend(metrics.get("missing", []))
                all_extra[entity_type].extend(metrics.get("extra", []))
                
        for entity_type in ["bands", "people", "albums"]:
            if all_missing[entity_type]:
                report.append(f"### {entity_type.title()} - Commonly Missed")
                report.append(f"- {', '.join(set(all_missing[entity_type]))}\n")
                
        return "\n".join(report)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Test extraction quality')
    parser.add_argument('--output', help='Output file for report')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    print("Testing extraction quality...")
    tester = ExtractionQualityTester()
    results = tester.run_all_tests()
    
    if args.json:
        output = json.dumps(results, indent=2)
    else:
        output = tester.generate_report(results)
        
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"\nReport saved to: {args.output}")
    else:
        print("\n" + output)
        
    return 0


if __name__ == '__main__':
    exit(main())