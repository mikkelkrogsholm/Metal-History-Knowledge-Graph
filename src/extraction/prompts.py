"""
Entity extraction prompts for metal history using magistral:24b
"""

# Main extraction prompt for nodes and relationships
ENTITY_EXTRACTION_PROMPT = """You are an expert at extracting structured information from text about metal music history. 

Extract all entities and relationships from the following text segment. Return ONLY valid JSON with no additional text.

Text segment:
{text}

Return a JSON object with this EXACT structure:
{{
  "entities": {{
    "bands": [
      {{
        "name": "string",
        "formed_year": number or null,
        "origin_city": "string or null",
        "origin_country": "string or null",
        "description": "brief description from text"
      }}
    ],
    "people": [
      {{
        "name": "string",
        "instruments": ["array of instruments"],
        "associated_bands": ["array of band names"],
        "description": "brief description"
      }}
    ],
    "albums": [
      {{
        "title": "string",
        "artist": "band or person name",
        "release_year": number or null,
        "release_date": "YYYY-MM-DD or null",
        "label": "string or null",
        "studio": "string or null",
        "description": "brief description"
      }}
    ],
    "songs": [
      {{
        "title": "string",
        "artist": "band or person name",
        "album": "album title or null",
        "bpm": number or null
      }}
    ],
    "subgenres": [
      {{
        "name": "string",
        "era_start": number or null,
        "era_end": number or null,
        "bpm_min": number or null,
        "bpm_max": number or null,
        "guitar_tuning": "string or null",
        "vocal_style": "string or null",
        "key_characteristics": "string",
        "parent_influences": ["array of genre names"]
      }}
    ],
    "locations": [
      {{
        "city": "string or null",
        "region": "string or null", 
        "country": "string",
        "scene_description": "brief description"
      }}
    ],
    "events": [
      {{
        "name": "string",
        "date": "YYYY-MM-DD or YYYY or null",
        "type": "festival/controversy/movement/other",
        "description": "brief description"
      }}
    ],
    "equipment": [
      {{
        "name": "string",
        "type": "guitar/pedal/amp/other",
        "specifications": "string or null"
      }}
    ],
    "studios": [
      {{
        "name": "string",
        "location": "string or null",
        "famous_for": "string"
      }}
    ],
    "labels": [
      {{
        "name": "string",
        "founded_year": number or null
      }}
    ]
  }},
  "relationships": [
    {{
      "type": "MEMBER_OF/FORMED_IN/RELEASED/PLAYS_GENRE/PRODUCED/RECORDED_AT/INFLUENCED_BY/EVOLVED_INTO/etc",
      "from": {{
        "entity_type": "band/person/album/etc",
        "name": "entity name"
      }},
      "to": {{
        "entity_type": "band/location/genre/etc", 
        "name": "entity name"
      }},
      "properties": {{
        "year": number or null,
        "role": "string or null",
        "context": "brief context from text"
      }}
    }}
  ]
}}

Guidelines:
- Extract ONLY information explicitly stated in the text
- Use null for missing information rather than guessing
- For dates, use YYYY-MM-DD format when full date is known, YYYY for just year
- Keep descriptions brief (1-2 sentences max)
- Include context in relationship properties
- BPM should be a number, not a range (extract min/max separately for genres)
"""

# Attribute enrichment prompt for additional details
ATTRIBUTE_ENRICHMENT_PROMPT = """Given this entity and the original text, extract any additional attributes or context.

Entity: {entity_type} - {entity_name}
Original text: {text}

Return ONLY a JSON object with additional attributes found in the text:
{{
  "attributes": {{
    "attribute_name": "value",
    ...
  }},
  "context": "relevant quote or context from the text"
}}

Focus on:
- Technical specifications (tunings, BPM, equipment details)
- Temporal information (dates, periods, durations)
- Quantitative data (chart positions, sales, view counts)
- Cultural context
- Notable achievements or milestones
"""

# Relationship validation prompt
RELATIONSHIP_VALIDATION_PROMPT = """Validate and enrich this relationship based on the text.

Relationship: {from_entity} {relationship_type} {to_entity}
Text: {text}

Return ONLY a JSON object:
{{
  "is_valid": true/false,
  "confidence": 0.0-1.0,
  "evidence": "quote from text supporting this relationship",
  "additional_properties": {{
    "property": "value"
  }}
}}
"""

# Text segmentation function
def segment_text(text: str, max_chars: int = 2000) -> list[dict]:
    """
    Segment text into manageable chunks for extraction.
    Tries to break at paragraph boundaries when possible.
    """
    paragraphs = text.split('\n\n')
    segments = []
    current_segment = []
    current_length = 0
    segment_id = 0
    
    for i, paragraph in enumerate(paragraphs):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
            
        # Check if adding this paragraph would exceed limit
        if current_length + len(paragraph) > max_chars and current_segment:
            # Save current segment
            segments.append({
                'id': segment_id,
                'text': '\n\n'.join(current_segment),
                'paragraph_nums': list(range(i - len(current_segment), i)),
                'char_count': current_length
            })
            segment_id += 1
            current_segment = [paragraph]
            current_length = len(paragraph)
        else:
            current_segment.append(paragraph)
            current_length += len(paragraph) + 2  # +2 for \n\n
    
    # Don't forget the last segment
    if current_segment:
        segments.append({
            'id': segment_id,
            'text': '\n\n'.join(current_segment),
            'paragraph_nums': list(range(len(paragraphs) - len(current_segment), len(paragraphs))),
            'char_count': current_length
        })
    
    return segments

# Contextual segmentation for better extraction
def segment_by_sections(text: str) -> list[dict]:
    """
    Segment text by section headers for more coherent extraction.
    Falls back to character limit if sections are too large.
    """
    lines = text.split('\n')
    segments = []
    current_section = []
    current_header = None
    segment_id = 0
    
    for i, line in enumerate(lines):
        # Detect section headers (lines starting with ##)
        if line.strip().startswith('##'):
            # Save previous section if exists
            if current_section:
                section_text = '\n'.join(current_section)
                # If section is too large, further segment it
                if len(section_text) > 3000:
                    sub_segments = segment_text(section_text, 2000)
                    for sub in sub_segments:
                        sub['section_header'] = current_header
                        sub['id'] = segment_id
                        segment_id += 1
                        segments.append(sub)
                else:
                    segments.append({
                        'id': segment_id,
                        'text': section_text,
                        'section_header': current_header,
                        'line_start': i - len(current_section),
                        'line_end': i,
                        'char_count': len(section_text)
                    })
                    segment_id += 1
            
            current_header = line.strip()
            current_section = [line]
        else:
            current_section.append(line)
    
    # Don't forget the last section
    if current_section:
        section_text = '\n'.join(current_section)
        if len(section_text) > 3000:
            sub_segments = segment_text(section_text, 2000)
            for sub in sub_segments:
                sub['section_header'] = current_header
                sub['id'] = segment_id
                segment_id += 1
                segments.append(sub)
        else:
            segments.append({
                'id': segment_id,
                'text': section_text,
                'section_header': current_header,
                'line_start': len(lines) - len(current_section),
                'line_end': len(lines),
                'char_count': len(section_text)
            })
    
    return segments