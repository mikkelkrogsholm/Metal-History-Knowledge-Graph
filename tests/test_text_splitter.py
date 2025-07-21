"""
Tests for text splitter functionality
"""

import pytest
from history.text_splitter import TextSplitter, TextChunk

class TestTextSplitter:
    
    def test_init_parameters(self):
        """Test TextSplitter initialization"""
        splitter = TextSplitter(chunk_size=3000, chunk_overlap=300, min_chunk_size=600)
        assert splitter.chunk_size == 3000
        assert splitter.chunk_overlap == 300
        assert splitter.min_chunk_size == 600
    
    def test_text_chunk_dataclass(self):
        """Test TextChunk dataclass"""
        chunk = TextChunk(
            id="test_001",
            source_file="test.md",
            chunk_index=0,
            text="Sample text",
            start_char=0,
            end_char=11,
            section_header="## Test Section"
        )
        
        assert chunk.id == "test_001"
        assert chunk.text == "Sample text"
        assert chunk.section_header == "## Test Section"
        
        # Test to_dict
        chunk_dict = chunk.to_dict()
        assert chunk_dict["char_count"] == 11
        assert chunk_dict["word_count"] == 2
    
    def test_split_by_sections(self):
        """Test splitting by markdown sections"""
        splitter = TextSplitter(chunk_size=1000)
        
        test_content = """# Title

## Section 1
This is the first section with some content about metal music.
It talks about the origins of heavy metal.

## Section 2
This is the second section discussing different subgenres.
Black metal, death metal, and thrash metal are mentioned.

### Subsection 2.1
More details about black metal specifically."""
        
        chunks = splitter._split_by_sections(test_content, "test.md")
        
        assert len(chunks) > 0
        assert any("## Section 1" in chunk.section_header for chunk in chunks if chunk.section_header)
        assert any("## Section 2" in chunk.section_header for chunk in chunks if chunk.section_header)
    
    def test_chunk_by_paragraphs(self):
        """Test chunking by paragraphs with overlap"""
        splitter = TextSplitter(chunk_size=200, chunk_overlap=50)
        
        test_content = """This is paragraph one about Black Sabbath.

This is paragraph two about Iron Maiden.

This is paragraph three about Judas Priest.

This is paragraph four about Metallica."""
        
        chunks = splitter._chunk_by_paragraphs(
            test_content, "test.md", "## Metal Bands", None, 0, 0
        )
        
        assert len(chunks) >= 2  # Should create multiple chunks
        # Check for overlap
        if len(chunks) > 1:
            # Some content should appear in multiple chunks due to overlap
            all_text = " ".join(chunk.text for chunk in chunks)
            assert len(all_text) > len(test_content)
    
    def test_simple_chunk_fallback(self):
        """Test simple chunking when no structure found"""
        splitter = TextSplitter(chunk_size=100, chunk_overlap=20)
        
        test_content = "A" * 300  # 300 characters, no structure
        
        chunks = splitter._simple_chunk(test_content, "test.md")
        
        assert len(chunks) >= 3  # Should create at least 3 chunks
        assert all(chunk.section_header is None for chunk in chunks)
    
    def test_min_chunk_size_respected(self):
        """Test that minimum chunk size is respected"""
        splitter = TextSplitter(chunk_size=1000, min_chunk_size=500)
        
        test_content = "Short content."  # Less than min size
        
        chunks = splitter._simple_chunk(test_content, "test.md")
        
        assert len(chunks) == 0  # Should not create chunks smaller than min size
    
    def test_split_document_integration(self):
        """Test full document splitting (requires test file)"""
        import tempfile
        import os
        
        splitter = TextSplitter(chunk_size=500, chunk_overlap=50)
        
        test_content = """# Metal History

## Early Days
Black Sabbath pioneered heavy metal in Birmingham.
They created a new sound that would influence generations.

## NWOBHM Era
The New Wave of British Heavy Metal brought bands like Iron Maiden.
This movement revitalized metal in the late 1970s and early 1980s.

### Key Bands
Iron Maiden, Saxon, and Diamond Head were instrumental.
They combined punk energy with metal heaviness."""
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(test_content)
            temp_path = f.name
        
        try:
            chunks = splitter.split_document(temp_path)
            
            assert len(chunks) > 0
            assert all(isinstance(chunk, TextChunk) for chunk in chunks)
            assert all(chunk.source_file == os.path.basename(temp_path) for chunk in chunks)
            
            # Check that chunks are properly indexed
            for i, chunk in enumerate(chunks):
                assert chunk.chunk_index == i
        
        finally:
            os.unlink(temp_path)