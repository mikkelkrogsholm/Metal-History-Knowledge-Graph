#!/usr/bin/env python3
"""
Text splitter for processing metal history documents into chunks
"""

import os
import json
from typing import List, Dict, Tuple
from dataclasses import dataclass
from pathlib import Path
import re

@dataclass
class TextChunk:
    """Represents a chunk of text from a document"""
    id: str
    source_file: str
    chunk_index: int
    text: str
    start_char: int
    end_char: int
    section_header: str = None
    subsection_header: str = None
    metadata: Dict = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'source_file': self.source_file,
            'chunk_index': self.chunk_index,
            'text': self.text,
            'start_char': self.start_char,
            'end_char': self.end_char,
            'section_header': self.section_header,
            'subsection_header': self.subsection_header,
            'metadata': self.metadata or {},
            'char_count': len(self.text),
            'word_count': len(self.text.split())
        }

class TextSplitter:
    """Split markdown documents into processable chunks"""
    
    def __init__(self, 
                 chunk_size: int = 2500,
                 chunk_overlap: int = 200,
                 min_chunk_size: int = 500):
        """
        Initialize text splitter
        
        Args:
            chunk_size: Target size for chunks in characters
            chunk_overlap: Number of characters to overlap between chunks
            min_chunk_size: Minimum chunk size to create
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def split_document(self, file_path: str) -> List[TextChunk]:
        """
        Split a single document into chunks
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            List of TextChunk objects
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        file_name = os.path.basename(file_path)
        
        # First, try to split by sections
        chunks = self._split_by_sections(content, file_name)
        
        # If no section-based splitting worked, fall back to simple chunking
        if not chunks:
            chunks = self._simple_chunk(content, file_name)
        
        return chunks
    
    def _split_by_sections(self, content: str, source_file: str) -> List[TextChunk]:
        """Split content by markdown sections (## and ###)"""
        chunks = []
        
        # Split by major sections (##)
        sections = re.split(r'^(##\s+[^\n]+)$', content, flags=re.MULTILINE)
        
        current_position = 0
        chunk_index = 0
        
        # Process sections
        for i in range(0, len(sections), 2):
            # Get section header and content
            if i == 0 and sections[i].strip():
                # Content before first section
                section_header = None
                section_content = sections[i]
            elif i + 1 < len(sections):
                section_header = sections[i+1].strip()
                section_content = sections[i+2] if i+2 < len(sections) else ""
            else:
                continue
            
            if not section_content.strip():
                continue
            
            # Split large sections by subsections (###)
            if len(section_content) > self.chunk_size * 1.5:
                subsection_chunks = self._split_by_subsections(
                    section_content, 
                    source_file, 
                    section_header,
                    current_position,
                    chunk_index
                )
                chunks.extend(subsection_chunks)
                chunk_index += len(subsection_chunks)
            else:
                # Create chunk for the entire section
                chunk = TextChunk(
                    id=f"{source_file}_{chunk_index:04d}",
                    source_file=source_file,
                    chunk_index=chunk_index,
                    text=section_content.strip(),
                    start_char=current_position,
                    end_char=current_position + len(section_content),
                    section_header=section_header
                )
                chunks.append(chunk)
                chunk_index += 1
            
            current_position += len(section_header or "") + len(section_content)
        
        return chunks
    
    def _split_by_subsections(self, 
                             content: str, 
                             source_file: str,
                             section_header: str,
                             start_position: int,
                             start_index: int) -> List[TextChunk]:
        """Split section content by subsections (###)"""
        chunks = []
        
        # Split by subsections
        subsections = re.split(r'^(###\s+[^\n]+)$', content, flags=re.MULTILINE)
        
        current_position = start_position
        chunk_index = start_index
        
        for i in range(0, len(subsections), 2):
            if i == 0 and subsections[i].strip():
                # Content before first subsection
                subsection_header = None
                subsection_content = subsections[i]
            elif i + 1 < len(subsections):
                subsection_header = subsections[i+1].strip()
                subsection_content = subsections[i+2] if i+2 < len(subsections) else ""
            else:
                continue
            
            if not subsection_content.strip():
                continue
            
            # If subsection is still too large, chunk it
            if len(subsection_content) > self.chunk_size:
                paragraph_chunks = self._chunk_by_paragraphs(
                    subsection_content,
                    source_file,
                    section_header,
                    subsection_header,
                    current_position,
                    chunk_index
                )
                chunks.extend(paragraph_chunks)
                chunk_index += len(paragraph_chunks)
            else:
                chunk = TextChunk(
                    id=f"{source_file}_{chunk_index:04d}",
                    source_file=source_file,
                    chunk_index=chunk_index,
                    text=subsection_content.strip(),
                    start_char=current_position,
                    end_char=current_position + len(subsection_content),
                    section_header=section_header,
                    subsection_header=subsection_header
                )
                chunks.append(chunk)
                chunk_index += 1
            
            current_position += len(subsection_header or "") + len(subsection_content)
        
        return chunks
    
    def _chunk_by_paragraphs(self,
                            content: str,
                            source_file: str,
                            section_header: str,
                            subsection_header: str,
                            start_position: int,
                            start_index: int) -> List[TextChunk]:
        """Chunk large text by paragraphs with overlap"""
        chunks = []
        paragraphs = content.split('\n\n')
        
        current_chunk = []
        current_size = 0
        chunk_index = start_index
        chunk_start = start_position
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_size = len(para)
            
            # If adding this paragraph exceeds chunk size
            if current_size + para_size > self.chunk_size and current_chunk:
                # Create chunk
                chunk_text = '\n\n'.join(current_chunk)
                chunk = TextChunk(
                    id=f"{source_file}_{chunk_index:04d}",
                    source_file=source_file,
                    chunk_index=chunk_index,
                    text=chunk_text,
                    start_char=chunk_start,
                    end_char=chunk_start + len(chunk_text),
                    section_header=section_header,
                    subsection_header=subsection_header
                )
                chunks.append(chunk)
                chunk_index += 1
                
                # Start new chunk with overlap
                if self.chunk_overlap > 0 and len(current_chunk) > 1:
                    # Keep last paragraph for overlap
                    overlap_text = current_chunk[-1]
                    current_chunk = [overlap_text, para]
                    current_size = len(overlap_text) + para_size
                    chunk_start = chunk_start + len(chunk_text) - len(overlap_text)
                else:
                    current_chunk = [para]
                    current_size = para_size
                    chunk_start = chunk_start + len(chunk_text) + 2  # +2 for \n\n
            else:
                current_chunk.append(para)
                current_size += para_size + 2  # +2 for paragraph separator
        
        # Don't forget the last chunk
        if current_chunk and current_size >= self.min_chunk_size:
            chunk_text = '\n\n'.join(current_chunk)
            chunk = TextChunk(
                id=f"{source_file}_{chunk_index:04d}",
                source_file=source_file,
                chunk_index=chunk_index,
                text=chunk_text,
                start_char=chunk_start,
                end_char=chunk_start + len(chunk_text),
                section_header=section_header,
                subsection_header=subsection_header
            )
            chunks.append(chunk)
        
        return chunks
    
    def _simple_chunk(self, content: str, source_file: str) -> List[TextChunk]:
        """Simple chunking when no structure is found"""
        chunks = []
        chunk_index = 0
        
        # Split by character count with overlap
        for i in range(0, len(content), self.chunk_size - self.chunk_overlap):
            chunk_end = min(i + self.chunk_size, len(content))
            
            # Try to end at a paragraph boundary
            if chunk_end < len(content):
                next_para = content.find('\n\n', chunk_end)
                if next_para != -1 and next_para - chunk_end < 200:
                    chunk_end = next_para
            
            chunk_text = content[i:chunk_end].strip()
            
            if len(chunk_text) >= self.min_chunk_size:
                chunk = TextChunk(
                    id=f"{source_file}_{chunk_index:04d}",
                    source_file=source_file,
                    chunk_index=chunk_index,
                    text=chunk_text,
                    start_char=i,
                    end_char=chunk_end
                )
                chunks.append(chunk)
                chunk_index += 1
        
        return chunks
    
    def split_multiple_documents(self, directory: str) -> Dict[str, List[TextChunk]]:
        """
        Split all markdown files in a directory
        
        Args:
            directory: Path to directory containing markdown files
            
        Returns:
            Dictionary mapping file names to their chunks
        """
        results = {}
        
        for file_path in Path(directory).glob('*.md'):
            print(f"\nProcessing: {file_path.name}")
            chunks = self.split_document(str(file_path))
            results[file_path.name] = chunks
            print(f"  Created {len(chunks)} chunks")
            
            # Print chunk statistics
            sizes = [len(chunk.text) for chunk in chunks]
            print(f"  Chunk sizes: min={min(sizes)}, max={max(sizes)}, avg={sum(sizes)/len(sizes):.0f}")
        
        return results

def main():
    """Test the text splitter"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Split metal history documents into chunks')
    parser.add_argument('--chunk-size', type=int, default=2500, help='Target chunk size in characters')
    parser.add_argument('--overlap', type=int, default=200, help='Overlap between chunks')
    parser.add_argument('--output', default='chunks.json', help='Output file for chunks')
    
    args = parser.parse_args()
    
    # Initialize splitter
    splitter = TextSplitter(
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap
    )
    
    # Process all documents in history folder
    history_dir = os.path.dirname(os.path.abspath(__file__))
    results = splitter.split_multiple_documents(history_dir)
    
    # Prepare output
    output_data = {
        'metadata': {
            'chunk_size': args.chunk_size,
            'chunk_overlap': args.overlap,
            'total_documents': len(results),
            'total_chunks': sum(len(chunks) for chunks in results.values())
        },
        'documents': {}
    }
    
    # Convert chunks to dictionaries
    for doc_name, chunks in results.items():
        output_data['documents'][doc_name] = [chunk.to_dict() for chunk in chunks]
    
    # Save to file
    output_path = os.path.join(history_dir, args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"Total documents processed: {len(results)}")
    print(f"Total chunks created: {output_data['metadata']['total_chunks']}")
    print(f"Output saved to: {output_path}")
    
    # Show sample chunks
    print(f"\nSample chunks from each document:")
    for doc_name, chunks in results.items():
        print(f"\n{doc_name}:")
        if chunks:
            sample = chunks[0]
            print(f"  First chunk ({sample.id}):")
            print(f"    Section: {sample.section_header}")
            print(f"    Size: {len(sample.text)} chars")
            print(f"    Preview: {sample.text[:100]}...")

if __name__ == "__main__":
    import sys
    if 'venv' not in sys.prefix:
        print("WARNING: Virtual environment not activated!")
        print("Run: source ../venv/bin/activate")
        sys.exit(1)
    
    main()