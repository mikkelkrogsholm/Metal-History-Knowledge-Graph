"""
Tests for measuring extraction quality metrics (precision, recall, F1)
"""

import pytest
import json
from pathlib import Path
import sys
from typing import Dict, List, Set, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from extraction.enhanced_extraction import extract_entities_enhanced
from extraction.extraction_schemas import ExtractionResult


class ExtractionQualityMetrics:
    """Calculate quality metrics for entity extraction"""
    
    def __init__(self):
        # Load ground truth data
        ground_truth_path = project_root / "tests" / "fixtures" / "ground_truth_data.json"
        with open(ground_truth_path) as f:
            self.ground_truth = json.load(f)
    
    def normalize_entity_name(self, name: str) -> str:
        """Normalize entity names for comparison"""
        return name.lower().strip().replace("'", "'")
    
    def calculate_entity_metrics(self, extracted: List[Dict], expected: List[Dict], 
                               entity_type: str) -> Dict[str, float]:
        """Calculate precision, recall, and F1 for a specific entity type"""
        # Extract names for comparison
        extracted_names = {self.normalize_entity_name(e.get("name", "")) 
                          for e in extracted if e.get("name")}
        expected_names = {self.normalize_entity_name(e.get("name", "")) 
                         for e in expected if e.get("name")}
        
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
            "support": len(expected_names)
        }
    
    def calculate_relationship_metrics(self, extracted_rels: List[Dict], 
                                     expected_rels: List[Dict]) -> Dict[str, float]:
        """Calculate metrics for relationship extraction"""
        # Create normalized relationship tuples
        def normalize_rel(rel):
            return (
                rel.get("type", "").upper(),
                self.normalize_entity_name(rel.get("from_entity", rel.get("from_entity_name", ""))),
                self.normalize_entity_name(rel.get("to_entity", rel.get("to_entity_name", "")))
            )
        
        extracted_rels_norm = {normalize_rel(r) for r in extracted_rels}
        expected_rels_norm = {normalize_rel(r) for r in expected_rels}
        
        # Calculate metrics
        true_positives = len(extracted_rels_norm & expected_rels_norm)
        false_positives = len(extracted_rels_norm - expected_rels_norm)
        false_negatives = len(expected_rels_norm - extracted_rels_norm)
        
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
            "support": len(expected_rels_norm)
        }
    
    def evaluate_extraction(self, text: str, test_case: Dict) -> Dict:
        """Evaluate extraction quality for a single test case"""
        # Extract entities
        result = extract_entities_enhanced(text)
        
        # Convert to dict format
        extracted_data = {
            "bands": [band.dict() for band in result.bands],
            "people": [person.dict() for person in result.people],
            "albums": [album.dict() for album in result.albums],
            "subgenres": [subgenre.dict() for subgenre in result.subgenres],
            "relationships": result.relationships
        }
        
        expected_data = test_case["expected_entities"]
        expected_rels = test_case.get("expected_relationships", [])
        
        # Calculate metrics for each entity type
        metrics = {}
        
        for entity_type in ["bands", "people", "albums", "subgenres"]:
            if entity_type in expected_data:
                metrics[entity_type] = self.calculate_entity_metrics(
                    extracted_data.get(entity_type, []),
                    expected_data.get(entity_type, []),
                    entity_type
                )
        
        # Calculate relationship metrics
        if expected_rels:
            metrics["relationships"] = self.calculate_relationship_metrics(
                extracted_data.get("relationships", []),
                expected_rels
            )
        
        # Calculate overall metrics
        all_precisions = [m["precision"] for m in metrics.values() if "precision" in m]
        all_recalls = [m["recall"] for m in metrics.values() if "recall" in m]
        all_f1s = [m["f1"] for m in metrics.values() if "f1" in m]
        
        metrics["overall"] = {
            "precision": sum(all_precisions) / len(all_precisions) if all_precisions else 0,
            "recall": sum(all_recalls) / len(all_recalls) if all_recalls else 0,
            "f1": sum(all_f1s) / len(all_f1s) if all_f1s else 0
        }
        
        return {
            "test_id": test_case["id"],
            "metrics": metrics,
            "extracted": extracted_data,
            "expected": expected_data
        }


class TestExtractionQuality:
    """Test extraction quality against ground truth"""
    
    @pytest.fixture
    def quality_metrics(self):
        return ExtractionQualityMetrics()
    
    def test_basic_extraction_accuracy(self, quality_metrics):
        """Test extraction accuracy on basic test cases"""
        results = []
        
        for test_case in quality_metrics.ground_truth["test_cases"][:3]:  # First 3 cases
            result = quality_metrics.evaluate_extraction(
                test_case["text"],
                test_case
            )
            results.append(result)
            
            # Print detailed results for debugging
            print(f"\nTest {test_case['id']}:")
            print(f"Text: {test_case['text'][:100]}...")
            print(f"Overall F1: {result['metrics']['overall']['f1']:.3f}")
            
            for entity_type, metrics in result['metrics'].items():
                if entity_type != "overall" and "f1" in metrics:
                    print(f"  {entity_type}: P={metrics['precision']:.3f}, "
                          f"R={metrics['recall']:.3f}, F1={metrics['f1']:.3f}")
        
        # Assert minimum quality thresholds
        overall_f1s = [r['metrics']['overall']['f1'] for r in results]
        avg_f1 = sum(overall_f1s) / len(overall_f1s)
        
        assert avg_f1 > 0.7, f"Average F1 score {avg_f1:.3f} is below threshold of 0.7"
        
    def test_complex_extraction_accuracy(self, quality_metrics):
        """Test extraction on more complex cases"""
        complex_cases = [tc for tc in quality_metrics.ground_truth["test_cases"] 
                        if tc["id"] in ["test_004", "test_005"]]
        
        for test_case in complex_cases:
            result = quality_metrics.evaluate_extraction(
                test_case["text"],
                test_case
            )
            
            # Complex cases might have lower accuracy but should still be reasonable
            assert result['metrics']['overall']['f1'] > 0.5, \
                f"F1 score for {test_case['id']} is too low"
            
    def test_edge_case_handling(self, quality_metrics):
        """Test extraction on edge cases like name variations"""
        edge_cases = quality_metrics.ground_truth["edge_cases"]
        
        for edge_case in edge_cases[:2]:  # Test first 2 edge cases
            # Extract entities
            result = extract_entities_enhanced(edge_case["text"])
            
            # Check specific edge case handling
            if edge_case["id"] == "edge_001":
                # Should recognize Black Sabbath despite misspelling
                band_names = [band.name for band in result.bands]
                assert any("Sabbath" in name for name in band_names), \
                    "Failed to extract Black Sabbath from misspelled text"
            
            elif edge_case["id"] == "edge_002":
                # Should extract multiple roles for Dave Mustaine
                people = [p for p in result.people if "Mustaine" in p.name]
                assert len(people) > 0, "Failed to extract Dave Mustaine"
                
                if people:
                    person = people[0]
                    assert len(person.instruments) >= 2, \
                        "Failed to extract multiple instruments for Dave Mustaine"
    
    def test_relationship_extraction_accuracy(self, quality_metrics):
        """Test relationship extraction specifically"""
        # Use test cases with relationships
        rel_test_cases = [tc for tc in quality_metrics.ground_truth["test_cases"]
                         if tc.get("expected_relationships")]
        
        relationship_metrics = []
        
        for test_case in rel_test_cases[:3]:
            result = quality_metrics.evaluate_extraction(
                test_case["text"],
                test_case
            )
            
            if "relationships" in result["metrics"]:
                rel_metrics = result["metrics"]["relationships"]
                relationship_metrics.append(rel_metrics)
                
                print(f"\nRelationship extraction for {test_case['id']}:")
                print(f"  Precision: {rel_metrics['precision']:.3f}")
                print(f"  Recall: {rel_metrics['recall']:.3f}")
                print(f"  F1: {rel_metrics['f1']:.3f}")
        
        # Calculate average relationship extraction metrics
        if relationship_metrics:
            avg_rel_f1 = sum(m['f1'] for m in relationship_metrics) / len(relationship_metrics)
            assert avg_rel_f1 > 0.6, \
                f"Average relationship F1 {avg_rel_f1:.3f} is below threshold"
    
    def test_extraction_consistency(self, quality_metrics):
        """Test that extraction is consistent across multiple runs"""
        test_text = "Iron Maiden formed in 1975 in London. Steve Harris played bass."
        
        # Run extraction multiple times
        results = []
        for _ in range(3):
            result = extract_entities_enhanced(test_text)
            results.append(result)
        
        # Check consistency
        band_names_sets = [{band.name for band in r.bands} for r in results]
        person_names_sets = [{person.name for person in r.people} for r in results]
        
        # All runs should produce the same entities
        assert all(s == band_names_sets[0] for s in band_names_sets), \
            "Inconsistent band extraction across runs"
        assert all(s == person_names_sets[0] for s in person_names_sets), \
            "Inconsistent person extraction across runs"
    
    @pytest.mark.parametrize("entity_type,min_f1", [
        ("bands", 0.8),
        ("people", 0.75),
        ("albums", 0.7),
        ("relationships", 0.6)
    ])
    def test_entity_type_minimum_quality(self, quality_metrics, entity_type, min_f1):
        """Test that each entity type meets minimum quality thresholds"""
        all_metrics = []
        
        for test_case in quality_metrics.ground_truth["test_cases"]:
            if entity_type in test_case.get("expected_entities", {}) or \
               (entity_type == "relationships" and test_case.get("expected_relationships")):
                result = quality_metrics.evaluate_extraction(
                    test_case["text"],
                    test_case
                )
                
                if entity_type in result["metrics"]:
                    all_metrics.append(result["metrics"][entity_type]["f1"])
        
        if all_metrics:
            avg_f1 = sum(all_metrics) / len(all_metrics)
            assert avg_f1 >= min_f1, \
                f"{entity_type} average F1 {avg_f1:.3f} is below minimum {min_f1}"