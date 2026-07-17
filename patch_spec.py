import re

with open("SPEC.md", "r") as f:
    spec = f.read()

# Update version in SPEC.md
spec = re.sub(r'\| Current version   \| `[0-9\.]+`\s+\|', '| Current version   | `0.1.3`                                            |', spec)
with open("SPEC.md", "w") as f:
    f.write(spec)

with open("CHANGELOG.md", "r") as f:
    changelog = f.read()

# Add new changelog entry
new_entry = """
## [0.1.3] - 2026-06-25

### Performance
- Replaced `Element.find()` with direct child iteration in `_joints.py`, `contact_helpers.py`, `postconditions.py`, and `bench_press_model.py` to bypass ElementPath regex overhead, speeding up model generation.
"""

changelog = changelog.replace("## [0.1.2]", new_entry.strip() + "\n\n## [0.1.2]")
with open("CHANGELOG.md", "w") as f:
    f.write(changelog)
