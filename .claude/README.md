# Claude Code Configuration

This directory contains Claude Code configurations for the Metal History project.

## Structure

```
.claude/
├── commands/           # Custom slash commands
│   ├── extract-entities.md      # Full extraction workflow
│   ├── test-extraction.md       # Quick extraction test
│   ├── init-database.md         # Database initialization
│   ├── process-chunks.md        # Text chunking workflow
│   ├── verify-deduplication.md  # Check deduplication quality
│   └── generate-embeddings.md   # Create vector embeddings
├── settings.json      # Tool permissions and preferences
└── README.md         # This file
```

## Using Custom Commands

Type `/` in Claude Code to see available commands. Project-specific commands include:

- `/project:extract-entities [--limit N]` - Run entity extraction
- `/project:test-extraction` - Quick test on sample data
- `/project:init-database` - Set up Kuzu database
- `/project:process-chunks [args]` - Create text chunks
- `/project:verify-deduplication` - Check entity merging
- `/project:generate-embeddings` - Create embeddings

## Tool Permissions

The `settings.json` file pre-approves common tools:
- File editing operations
- Python and pytest execution
- Git operations
- Ollama model interactions
- Virtual environment commands

## Adding New Commands

1. Create a new `.md` file in `commands/`
2. Use `$ARGUMENTS` placeholder for parameters
3. Include clear instructions and examples
4. Test the command with various inputs

## Sharing Configuration

This configuration is checked into git, so all team members get:
- Same tool permissions
- Same custom commands
- Consistent workflow patterns

To override locally, create `.claude/settings.local.json` (gitignored).