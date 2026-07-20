import re
from datetime import datetime

with open('SPEC.md', 'r') as f:
    content = f.read()

# Update version in the table
current_version_match = re.search(r'\|\s*Current version\s*\|\s*`([\d.]+)`\s*\|', content)
if current_version_match:
    current_version = current_version_match.group(1)
    parts = current_version.split('.')
    parts[-1] = str(int(parts[-1]) + 1)
    new_version = '.'.join(parts)
    content = content.replace(f'| Current version   | `{current_version}`', f'| Current version   | `{new_version}`')
else:
    print("Could not find version")
    exit(1)

# Add changelog entry
date_str = datetime.now().strftime('%Y-%m-%d')
timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

changelog_header = """| Date       | Version | Notes                                                                                                                                                                                                                                                        |
| ---------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |"""
new_entry = f"\n| {date_str} | {new_version}  | Optimized `require_finite` validation function in `preconditions.py` by adding a fast path for shape-6 numpy arrays using `.item()` to manually unroll checks, resulting in a ~1.8x speedup for 6-DOF arrays.                                                |"

content = content.replace(changelog_header, changelog_header + new_entry)

# Update the timestamp
content = re.sub(r'<!-- Updated: .*? -->', f'<!-- Updated: {timestamp} -->', content)

with open('SPEC.md', 'w') as f:
    f.write(content)
