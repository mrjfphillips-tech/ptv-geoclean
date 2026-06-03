---
inclusion: auto
---

# Git Commit Rule

## MANDATORY: Commit before ending any session

Before ending any work session or when the user says goodbye/done/finished:

1. Stage all changed files: `git add -A`
2. Commit with a descriptive message summarizing what was done
3. Push to remote: `git push`

## MANDATORY: Commit after significant changes

After completing any of these, immediately commit:
- Any file creation or deletion
- Any feature implementation
- Any bug fix
- Any configuration change
- Any UI/styling change

Use format: `git commit -m "feat: description"` or `git commit -m "fix: description"`

## NEVER use PowerShell for file content manipulation

- NEVER use PowerShell's `-replace` operator on files with Unicode/emoji content
- NEVER use `Set-Content` or `Get-Content -Raw` for editing source files
- ALWAYS use the str_replace, fs_write, or fs_append tools for file edits
- PowerShell mangles UTF-8 content and can destroy files silently
