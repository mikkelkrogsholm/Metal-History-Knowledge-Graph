#!/bin/bash
# Setup script to install git hooks when repository is initialized

echo "🔧 Setting up git hooks for Metal History project..."

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository!"
    echo "Please run 'git init' first, then run this script again."
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p .git/hooks

# Copy pre-commit hook
if [ -f "scripts/hooks/pre-commit" ]; then
    cp scripts/hooks/pre-commit .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
    echo "✅ Pre-commit hook installed"
else
    echo "❌ Error: scripts/hooks/pre-commit not found!"
    exit 1
fi

# Optional: Create commit-msg hook for conventional commits
cat > .git/hooks/commit-msg << 'EOF'
#!/bin/bash
# Validates commit message format

commit_regex='^(feat|fix|docs|style|refactor|test|chore)(\(.+\))?: .{1,50}'

if ! grep -qE "$commit_regex" "$1"; then
    echo "❌ Invalid commit message format!"
    echo "Format: <type>(<scope>): <subject>"
    echo "Types: feat, fix, docs, style, refactor, test, chore"
    echo "Example: feat(extraction): add support for live albums"
    exit 1
fi
EOF

chmod +x .git/hooks/commit-msg
echo "✅ Commit-msg hook installed"

echo ""
echo "🎉 Git hooks setup complete!"
echo ""
echo "Hooks installed:"
echo "  - pre-commit: Runs tests and validation before commits"
echo "  - commit-msg: Enforces conventional commit format"
echo ""
echo "To skip hooks temporarily, use: git commit --no-verify"