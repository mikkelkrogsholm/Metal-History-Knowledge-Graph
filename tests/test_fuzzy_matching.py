"""
Tests for fuzzy matching functionality
"""

import pytest
from pipeline.extraction_pipeline import FuzzyMatcher

class TestFuzzyMatcher:
    
    def test_exact_match(self):
        """Test exact string matching"""
        matcher = FuzzyMatcher()
        assert matcher.calculate_similarity("Black Sabbath", "Black Sabbath") == 1.0
        assert matcher.are_similar("Black Sabbath", "Black Sabbath") is True
    
    def test_case_insensitive(self):
        """Test case insensitive matching"""
        matcher = FuzzyMatcher()
        assert matcher.calculate_similarity("black sabbath", "BLACK SABBATH") == 1.0
        assert matcher.are_similar("Iron Maiden", "iron maiden") is True
    
    def test_whitespace_normalization(self):
        """Test whitespace handling"""
        matcher = FuzzyMatcher()
        assert matcher.calculate_similarity("Black  Sabbath", "Black Sabbath") == 1.0
        assert matcher.calculate_similarity(" Metallica ", "Metallica") == 1.0
    
    def test_typos(self):
        """Test matching with typos"""
        matcher = FuzzyMatcher(similarity_threshold=0.85)
        
        test_cases = [
            ("Black Sabbath", "Black Sabath", True),    # Missing 'b'
            ("Judas Priest", "Judas Preist", True),     # Transposed 'ei'
            ("Metallica", "Metalica", True),            # Missing 'l'
            ("Megadeth", "Megadeath", True),            # Common misspelling
        ]
        
        for name1, name2, expected in test_cases:
            similarity = matcher.calculate_similarity(name1, name2)
            result = matcher.are_similar(name1, name2)
            assert result == expected, f"{name1} vs {name2}: {similarity:.2f}"
    
    def test_special_characters(self):
        """Test matching with special characters"""
        matcher = FuzzyMatcher()
        
        assert matcher.calculate_similarity("Motörhead", "Motorhead") > 0.85
        assert matcher.calculate_similarity("AC/DC", "ACDC") > 0.85
        assert matcher.are_similar("Guns N' Roses", "Guns N Roses") is True
    
    def test_plurals(self):
        """Test matching with plurals"""
        matcher = FuzzyMatcher()
        
        assert matcher.are_similar("Iron Maiden", "Iron Maidens") is True
        assert matcher.are_similar("Black Label Society", "Black Label Societies") is True
    
    def test_threshold_behavior(self):
        """Test similarity threshold"""
        matcher_strict = FuzzyMatcher(similarity_threshold=0.95)
        matcher_loose = FuzzyMatcher(similarity_threshold=0.70)
        
        # These are 92% similar
        assert matcher_strict.are_similar("Dream Theater", "Dream Theatre") is False
        assert matcher_loose.are_similar("Dream Theater", "Dream Theatre") is True
    
    def test_find_best_match(self):
        """Test finding best match from candidates"""
        matcher = FuzzyMatcher()
        
        candidates = [
            "Black Sabbath",
            "Black Label Society", 
            "Sabbath Bloody Sabbath",
            "Deep Purple",
            "Black Flag"
        ]
        
        # Test exact match
        best, score = matcher.find_best_match("Black Sabbath", candidates)
        assert best == "Black Sabbath"
        assert score == 1.0
        
        # Test fuzzy match
        best, score = matcher.find_best_match("Black Sabath", candidates)
        assert best == "Black Sabbath"
        assert score > 0.9
        
        # Test no match above threshold
        result = matcher.find_best_match("Iron Maiden", candidates)
        assert result is None
    
    def test_empty_strings(self):
        """Test handling of empty strings"""
        matcher = FuzzyMatcher()
        
        assert matcher.calculate_similarity("", "") == 1.0
        assert matcher.calculate_similarity("Black Sabbath", "") == 0.0
        assert matcher.calculate_similarity("", "Black Sabbath") == 0.0
    
    def test_unicode_handling(self):
        """Test handling of unicode characters"""
        matcher = FuzzyMatcher()
        
        # Nordic characters
        assert matcher.are_similar("Björk", "Bjork") is True
        
        # Different spellings
        assert matcher.are_similar("Queensrÿche", "Queensryche") is True