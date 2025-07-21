Work on GitHub epic: $ARGUMENTS

Follow these steps:

1. Use `gh issue view $ARGUMENTS` to fetch the epic details and display it.

2. Parse the epic to find all linked issues (#\d+ patterns).

3. For each issue, use `gh issue view` to check if it's open or closed.

4. If resuming work, check git log for commits mentioning epic issues to determine the last worked item.

5. Select the next open issue and display: "Starting work on issue #{number}: {title}"

6. Create a branch: `git checkout -b epic-{epic-number}-issue-{issue-number}`

7. Use `gh issue view {issue-number}` to display full issue details.

8. Begin implementation. When complete:
   - Run tests
   - Commit with message: "Epic #{epic}: Complete issue #{issue} - {description}"
   - Create PR using `gh pr create --title "Epic #{epic}: {issue title}" --body "Closes #{issue}"`

9. After PR creation, offer to continue with the next issue or stop.

Remember to use descriptive commit messages linking both epic and issue numbers for tracking.