# Debug Extraction Command

This command helps debug entity extraction issues.

## Usage
```
/debug-extraction [text|file|chunk_id]
```

## Description
Debugs entity extraction problems by analyzing extraction results, prompts, and model responses.

## Options
- Provide text directly to test extraction
- Specify a file path to extract from
- Give a chunk ID to review specific extraction

## Examples
```
/debug-extraction "Black Sabbath formed in 1968"
/debug-extraction chunk_12345
/debug-extraction history/test_snippet.md
```

## Tasks
1. Run extraction on provided input
2. Show raw LLM response
3. Display parsed entities
4. Identify extraction failures
5. Suggest prompt improvements