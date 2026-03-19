---
description: Update plugin version and push changes to git
allowed-tools: Read, Edit, Bash, AskUserQuestion
---

## Instructions

1. Read the current version from `plugin/.claude-plugin/plugin.json`

2. Ask the user what type of version bump they want:
   - patch (x.y.Z) - bug fixes, minor updates
   - minor (x.Y.0) - new features, backwards compatible
   - major (X.0.0) - breaking changes

3. Calculate the new version based on their choice

4. Update the version in `plugin/.claude-plugin/plugin.json`

5. Create a git commit with message: "Bump version to {new_version}"

6. Push the changes to the remote repository

7. Report the completed version update to the user
