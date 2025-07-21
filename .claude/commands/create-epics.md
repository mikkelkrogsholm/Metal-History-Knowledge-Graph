---
allowed-tools: Bash(git status), Bash(git branch), Bash(gh issue list), Bash(gh label list), Bash(find), Bash(grep)
description: Create a well-structured epic with properly scoped issues
---

Please help me create an epic for: $ARGUMENTS.

## Context Gathering
- Current branch: !`git branch --show-current`
- Recent commits: !`git log --oneline -10`
- Open issues: !`gh issue list --limit 10`
- Available labels: !`gh label list`

## Phase 1: Deep Analysis

1. **Understand the epic scope**:
   - Parse the epic description to identify key components and goals
   - Check @README.md and @CLAUDE.md for project conventions
   - Review @package.json or equivalent for tech stack context
   - Identify if this relates to existing features or is entirely new

2. **Research implementation patterns**:
   - Search for similar features: !`find . -type f -name "*.js" -o -name "*.ts" | xargs grep -l "PATTERN" | head -10`
   - Review relevant modules and their structure
   - Check @docs/ folder for architecture decisions
   - Note testing patterns from @__tests__/ or @test/ directories

3. **Identify constraints and dependencies**:
   - Check for related open issues: !`gh issue list --search "KEYWORDS"`
   - Review recent PRs for context: !`gh pr list --state merged --limit 5`
   - Consider performance, security, and accessibility requirements
   - Note any external API or service dependencies

## Phase 2: Strategic Planning

4. **Create implementation strategy**:
   - Design high-level approach (max 3-5 sentences)
   - Identify the critical path and dependencies
   - Consider MVP vs full implementation
   - Plan for incremental delivery of value

5. **Break down into issues** (3-7 total, following INVEST principles):
   - Each issue should be:
     - Independent (minimal dependencies)
     - Negotiable (flexible implementation)
     - Valuable (delivers user/business value)
     - Estimable (clear scope)
     - Small (1-3 days of work)
     - Testable (clear acceptance criteria)

## Phase 3: Issue Creation

6. **For each issue, structure as**:
   ```markdown
   ## Description
   [2-3 sentences explaining the what and why]

   ## Acceptance Criteria
   - [ ] Specific, measurable outcome 1
   - [ ] Specific, measurable outcome 2
   - [ ] Tests are written and passing

   ## Technical Notes
   - Implementation approach (if not obvious)
   - Files/modules to modify
   - Potential gotchas

   ## Definition of Done
   - [ ] Code reviewed and approved
   - [ ] Tests written and passing
   - [ ] Documentation updated
   - [ ] No linting errors
   ```

7. **Create issues with proper metadata**:
   ```bash
   gh issue create \
     --title "[Epic: EPIC_NAME] Issue Title" \
     --body "issue content" \
     --label "enhancement,epic:EPIC_NAME" \
     --assignee @me
   ```

8. **Create epic tracking issue**:
   - Create a parent issue listing all child issues
   - Use task list format for easy progress tracking
   - Add epic label and milestone if applicable

## Phase 4: Documentation & Handoff

9. **Update project documentation**:
   - Add epic overview to @CLAUDE.md if significant
   - Update relevant docs with planned changes
   - Create ADR (Architecture Decision Record) if needed

10. **Generate summary report**:
    ```markdown
    # Epic: [EPIC_NAME] - Implementation Plan
    
    ## Overview
    [1-2 sentence summary]
    
    ## Issues Created
    - [ ] #123: Issue 1 Title (Size: S)
    - [ ] #124: Issue 2 Title (Size: M)
    - [ ] #125: Issue 3 Title (Size: S)
    
    ## Implementation Order
    1. Start with #123 (foundation)
    2. Then #124 (core feature)
    3. Finally #125 (polish)
    
    ## Success Metrics
    - [How we'll measure success]
    ```

## Principles
- Prefer proven patterns from the codebase over novel solutions
- Each issue should provide value even if later issues are deprioritized
- Include testing and documentation in issue scope, not as separate issues
- Consider the reviewer's perspective - make PRs easy to review

Remember: Start with the simplest thing that could possibly work, then iterate.