"""
End-to-end integration tests for the complete extraction pipeline
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from history.text_splitter import TextSplitter, TextChunk
from pipeline.extraction_pipeline import ExtractionPipeline
from extraction.extraction_schemas import ExtractionResult, Band, Person, Album
from extraction.enhanced_extraction import extract_entities_enhanced
from scripts.automation.entity_validation import validate_entities
from scripts.automation.generate_embeddings import EmbeddingGenerator
import kuzu


class TestEndToEndPipeline:
    """Test the complete pipeline from document splitting to database loading"""
    
    @pytest.fixture
    def sample_documents(self):
        """Create sample metal history documents for testing"""
        return {
            "heavy_metal_origins.md": """# Heavy Metal Origins

## The Birth of Metal (1968-1970)

Black Sabbath formed in Birmingham, England in 1968. The band consisted of Tony Iommi on guitar, 
Geezer Butler on bass, Bill Ward on drums, and Ozzy Osbourne on vocals. They are widely considered 
the pioneers of heavy metal music.

Their self-titled debut album "Black Sabbath" was released on February 13, 1970, which many consider 
the first true heavy metal album. The album featured dark themes and heavy, distorted guitar riffs 
that would define the genre.

## Early Influences

Led Zeppelin, formed in 1968, also contributed to the development of heavy metal with their heavy 
blues-rock sound. Jimmy Page's guitar work and Robert Plant's powerful vocals influenced countless 
metal bands that followed.

Deep Purple, another British band, released "In Rock" in 1970, featuring the classic lineup with 
Ian Gillan on vocals and Ritchie Blackmore on guitar. Their song "Speed King" showcased the fast, 
aggressive style that would influence later metal subgenres.""",
            
            "nwobhm_movement.md": """# New Wave of British Heavy Metal

## The Movement Begins (1979-1981)

The New Wave of British Heavy Metal (NWOBHM) emerged in the late 1970s as a reaction to the 
decline of early heavy metal bands and the punk rock movement. This movement revitalized heavy 
metal in the UK and influenced metal worldwide.

### Key Bands

Iron Maiden formed in Leyton, East London, on Christmas Day 1975 by bassist Steve Harris. 
However, they didn't release their self-titled debut album until 1980. The album featured 
Paul Di'Anno on vocals and included classics like "Phantom of the Opera" and "Iron Maiden."

Def Leppard, from Sheffield, formed in 1977. Their debut album "On Through the Night" was 
released in 1980, showcasing a more melodic approach to heavy metal that would later evolve 
into their signature sound.

Saxon formed in 1977 in Barnsley, South Yorkshire. They released their self-titled debut 
album in 1979, followed by "Wheels of Steel" in 1980, which included their anthem "747 
(Strangers in the Night)."

## Impact on Metal

The NWOBHM movement emphasized DIY ethics, faster tempos, and a return to heavy metal's 
aggressive roots while incorporating the energy of punk rock. This movement directly influenced 
the development of thrash metal in the United States."""
        }
    
    @pytest.fixture
    def temp_test_dir(self):
        """Create a temporary directory for test files"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_complete_pipeline_small_dataset(self, sample_documents, temp_test_dir):
        """Test the complete pipeline with a small dataset"""
        # Step 1: Save sample documents
        doc_dir = temp_test_dir / "documents"
        doc_dir.mkdir()
        
        for filename, content in sample_documents.items():
            (doc_dir / filename).write_text(content)
        
        # Step 2: Split documents into chunks
        splitter = TextSplitter(chunk_size=500, chunk_overlap=50)
        all_chunks = []
        
        for doc_path in doc_dir.glob("*.md"):
            content = doc_path.read_text()
            chunks = splitter.split_text(content, source_file=doc_path.name)
            all_chunks.extend(chunks)
        
        # Save chunks
        chunks_file = temp_test_dir / "chunks.json"
        chunks_data = {
            "metadata": {
                "chunk_size": 500,
                "chunk_overlap": 50,
                "total_documents": len(sample_documents),
                "total_chunks": len(all_chunks)
            },
            "documents": {}
        }
        
        for chunk in all_chunks:
            doc_name = chunk.source_file
            if doc_name not in chunks_data["documents"]:
                chunks_data["documents"][doc_name] = []
            chunks_data["documents"][doc_name].append(chunk.to_dict())
        
        chunks_file.write_text(json.dumps(chunks_data, indent=2))
        
        # Verify chunks were created
        assert chunks_file.exists()
        assert len(all_chunks) > 4  # Should have multiple chunks
        
        # Step 3: Extract entities from chunks
        pipeline = ExtractionPipeline(chunks_file=str(chunks_file))
        extracted_file = temp_test_dir / "extracted_entities.json"
        
        # Process all chunks (small dataset)
        results = pipeline.process_chunks(output_file=str(extracted_file))
        
        # Verify extraction results
        assert extracted_file.exists()
        extracted_data = json.loads(extracted_file.read_text())
        
        assert "entities" in extracted_data
        assert "bands" in extracted_data["entities"]
        assert "people" in extracted_data["entities"]
        assert "metadata" in extracted_data
        
        # Check for expected entities
        band_names = {band["name"] for band in extracted_data["entities"]["bands"]}
        assert "Black Sabbath" in band_names
        assert "Iron Maiden" in band_names
        
        people_names = {person["name"] for person in extracted_data["entities"]["people"]}
        assert any("Tony Iommi" in name or "Iommi" in name for name in people_names)
        
        # Step 4: Validate entities
        validation_report = validate_entities(str(extracted_file))
        
        # Check validation results
        assert validation_report["summary"]["total_entities"] > 0
        assert validation_report["summary"]["bands"]["count"] > 0
        assert validation_report["summary"]["people"]["count"] > 0
        
        # Step 5: Generate embeddings (mock for speed)
        embeddings_file = temp_test_dir / "entities_with_embeddings.json"
        
        # For testing, we'll create mock embeddings
        entities_with_embeddings = extracted_data.copy()
        for entity_type, entities in entities_with_embeddings["entities"].items():
            for entity in entities:
                # Mock embedding - in real test would use actual embedding model
                entity["embedding"] = [0.1] * 1024  # Snowflake Arctic Embed2 dimensions
        
        embeddings_file.write_text(json.dumps(entities_with_embeddings, indent=2))
        
        # Step 6: Load to Kuzu database
        db_path = temp_test_dir / "test_metal_history.db"
        db = kuzu.Database(str(db_path))
        conn = kuzu.Connection(db)
        
        # Create schema (simplified for testing)
        conn.execute("""
            CREATE NODE TABLE Band(
                name STRING PRIMARY KEY,
                formed_year INT64,
                origin_city STRING,
                origin_country STRING,
                description STRING,
                embedding FLOAT[1024]
            )
        """)
        
        conn.execute("""
            CREATE NODE TABLE Person(
                name STRING PRIMARY KEY,
                birth_year INT64,
                death_year INT64,
                birth_place STRING,
                description STRING,
                instruments STRING[],
                embedding FLOAT[1024]
            )
        """)
        
        conn.execute("""
            CREATE REL TABLE MEMBER_OF(
                FROM Person TO Band,
                start_year INT64,
                end_year INT64,
                roles STRING[],
                is_founding_member BOOLEAN
            )
        """)
        
        # Load bands
        for band in entities_with_embeddings["entities"]["bands"]:
            conn.execute(
                "CREATE (b:Band {name: $name, formed_year: $year, description: $desc, embedding: $emb})",
                {
                    "name": band["name"],
                    "year": band.get("formed_year"),
                    "desc": band.get("description", ""),
                    "emb": band["embedding"]
                }
            )
        
        # Verify data was loaded
        result = conn.execute("MATCH (b:Band) RETURN COUNT(b) as count")
        band_count = result.get_next()[0]
        assert band_count >= 5  # At least Black Sabbath, Iron Maiden, Led Zeppelin, Deep Purple, Def Leppard
        
        # Test vector similarity search
        query_embedding = [0.1] * 1024  # Mock query embedding
        result = conn.execute("""
            MATCH (b:Band)
            RETURN b.name, 
                   array_cosine_similarity(b.embedding, $query_emb) as similarity
            ORDER BY similarity DESC
            LIMIT 5
        """, {"query_emb": query_embedding})
        
        similar_bands = []
        while result.has_next():
            row = result.get_next()
            similar_bands.append({"name": row[0], "similarity": row[1]})
        
        assert len(similar_bands) > 0
        
    def test_pipeline_error_recovery(self, temp_test_dir):
        """Test pipeline's ability to recover from errors"""
        # Create a chunks file with some invalid data
        chunks_data = {
            "metadata": {"total_chunks": 3},
            "documents": {
                "test.md": [
                    {"id": "valid_1", "text": "Black Sabbath formed in 1968.", "chunk_index": 0},
                    {"id": "invalid_1", "text": "", "chunk_index": 1},  # Empty text
                    {"id": "valid_2", "text": "Iron Maiden formed in 1975.", "chunk_index": 2}
                ]
            }
        }
        
        chunks_file = temp_test_dir / "chunks_with_errors.json"
        chunks_file.write_text(json.dumps(chunks_data))
        
        # Process with pipeline - should handle empty chunks gracefully
        pipeline = ExtractionPipeline(chunks_file=str(chunks_file))
        extracted_file = temp_test_dir / "extracted_with_errors.json"
        
        results = pipeline.process_chunks(output_file=str(extracted_file))
        
        # Should still extract from valid chunks
        assert extracted_file.exists()
        extracted_data = json.loads(extracted_file.read_text())
        
        band_names = {band["name"] for band in extracted_data["entities"]["bands"]}
        assert len(band_names) >= 2  # Should have at least Black Sabbath and Iron Maiden
        
    def test_pipeline_deduplication(self, temp_test_dir):
        """Test the pipeline's entity deduplication capabilities"""
        # Create chunks with duplicate entities (name variations)
        chunks_data = {
            "metadata": {"total_chunks": 3},
            "documents": {
                "doc1.md": [
                    {
                        "id": "chunk_1",
                        "text": "Black Sabbath formed in Birmingham in 1968. Tony Iommi played guitar.",
                        "chunk_index": 0
                    }
                ],
                "doc2.md": [
                    {
                        "id": "chunk_2", 
                        "text": "Black Sabath (often misspelled) pioneered heavy metal. Tony Iommi was the guitarist.",
                        "chunk_index": 0
                    }
                ],
                "doc3.md": [
                    {
                        "id": "chunk_3",
                        "text": "BLACK SABBATH released their first album in 1970. T. Iommi created the heavy sound.",
                        "chunk_index": 0
                    }
                ]
            }
        }
        
        chunks_file = temp_test_dir / "chunks_duplicates.json"
        chunks_file.write_text(json.dumps(chunks_data))
        
        # Process chunks
        pipeline = ExtractionPipeline(chunks_file=str(chunks_file))
        extracted_file = temp_test_dir / "extracted_deduplicated.json"
        
        results = pipeline.process_chunks(output_file=str(extracted_file))
        
        # Check deduplication worked
        extracted_data = json.loads(extracted_file.read_text())
        
        # Should have only one Black Sabbath entity (deduplicated)
        bands = extracted_data["entities"]["bands"]
        sabbath_entries = [b for b in bands if "Sabbath" in b["name"]]
        assert len(sabbath_entries) == 1
        
        # Should have metadata about variations
        sabbath = sabbath_entries[0]
        assert "_metadata" in sabbath
        assert len(sabbath["_metadata"]["variations"]) >= 2  # At least 2 name variations
        assert len(sabbath["_metadata"]["source_chunks"]) == 3  # From all 3 chunks
        
        # Should have only one Tony Iommi entity
        people = extracted_data["entities"]["people"]
        iommi_entries = [p for p in people if "Iommi" in p["name"]]
        assert len(iommi_entries) == 1
        
    @pytest.mark.slow
    def test_pipeline_performance_benchmark(self, sample_documents, temp_test_dir):
        """Benchmark pipeline performance with timing measurements"""
        import time
        
        # Create a larger dataset by duplicating content
        large_content = "\n\n".join(sample_documents.values()) * 5  # 5x the content
        
        # Split into chunks
        splitter = TextSplitter(chunk_size=1000, chunk_overlap=100)
        
        start_time = time.time()
        chunks = splitter.split_text(large_content, source_file="large_test.md")
        split_time = time.time() - start_time
        
        # Save chunks
        chunks_file = temp_test_dir / "large_chunks.json"
        chunks_data = {
            "metadata": {"total_chunks": len(chunks)},
            "documents": {
                "large_test.md": [chunk.to_dict() for chunk in chunks]
            }
        }
        chunks_file.write_text(json.dumps(chunks_data))
        
        # Extract entities (limit to 10 chunks for testing)
        pipeline = ExtractionPipeline(chunks_file=str(chunks_file))
        
        start_time = time.time()
        results = pipeline.process_chunks(limit=10, output_file=str(temp_test_dir / "perf_test.json"))
        extract_time = time.time() - start_time
        
        # Performance assertions
        assert split_time < 1.0  # Splitting should be fast
        assert extract_time < 120  # 10 chunks should process in under 2 minutes
        
        # Log performance metrics
        print(f"\nPerformance Metrics:")
        print(f"- Document splitting: {split_time:.2f}s for {len(chunks)} chunks")
        print(f"- Entity extraction: {extract_time:.2f}s for 10 chunks")
        print(f"- Average per chunk: {extract_time/10:.2f}s")
        
    def test_pipeline_data_consistency(self, temp_test_dir):
        """Test that data remains consistent through the pipeline"""
        # Create test data with specific relationships
        chunks_data = {
            "metadata": {"total_chunks": 1},
            "documents": {
                "relationships.md": [
                    {
                        "id": "rel_test",
                        "text": """Black Sabbath formed in 1968 with Tony Iommi on guitar, 
                        Geezer Butler on bass, Bill Ward on drums, and Ozzy Osbourne on vocals.
                        They released their album 'Paranoid' in 1970, which included the song 'Iron Man'.""",
                        "chunk_index": 0
                    }
                ]
            }
        }
        
        chunks_file = temp_test_dir / "chunks_relationships.json"
        chunks_file.write_text(json.dumps(chunks_data))
        
        # Process
        pipeline = ExtractionPipeline(chunks_file=str(chunks_file))
        extracted_file = temp_test_dir / "extracted_relationships.json"
        
        results = pipeline.process_chunks(output_file=str(extracted_file))
        extracted_data = json.loads(extracted_file.read_text())
        
        # Verify relationships were extracted
        assert "relationships" in extracted_data
        relationships = extracted_data["relationships"]
        
        # Should have MEMBER_OF relationships
        member_rels = [r for r in relationships if r["type"] == "MEMBER_OF"]
        assert len(member_rels) >= 4  # 4 members of Black Sabbath
        
        # Should have RELEASED relationships
        released_rels = [r for r in relationships if r["type"] == "RELEASED"]
        assert len(released_rels) >= 1  # Black Sabbath released Paranoid
        
        # Verify data integrity
        for rel in member_rels:
            assert "from_entity_name" in rel
            assert "to_entity_name" in rel
            assert rel["to_entity_name"] == "Black Sabbath"