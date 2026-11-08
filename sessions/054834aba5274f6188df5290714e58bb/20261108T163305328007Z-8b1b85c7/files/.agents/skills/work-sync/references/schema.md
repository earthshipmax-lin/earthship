# Event schema

```markdown
# <short descriptive title>
- Time: <UTC ISO timestamp>
- Session: <unique label>
- Category: <one canonical category>
- Goal / user instruction: <sanitized summary>
- Action: <what was attempted; command + cwd when applicable>
- Result: <observed output and exit code, or unknown/in progress>
- Evidence: <file, test log, source URL or commit>
- Decision and reason: <if applicable>
- Next: <concrete resumption step>
```

Use UTC in stored events; present times in the user's timezone. Never put access tokens in command examples. Source edits are captured under `files/` in each snapshot. Logs, binary files, ignored files and large files are excluded by default; summarize important results into events. This format is agent-neutral.
