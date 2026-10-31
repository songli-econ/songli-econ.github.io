#!/usr/bin/env python3
"""Set profile modification metadata from its latest source commit."""
import re
import subprocess
from datetime import datetime
from pathlib import Path

root = Path(__file__).resolve().parents[1]
rows = subprocess.check_output(
    ['git', 'log', '--format=%cI%x09%s', '--', 'index.html'],
    cwd=root, text=True,
).splitlines()
stamp = next(row.split('\t', 1)[0] for row in rows
             if row.split('\t', 1)[1] != 'Sync profile modification metadata')
date = datetime.fromisoformat(stamp)
page = root / 'index.html'
text = page.read_text()
text, count = re.subn(r'("dateModified": ")[^"]+(" )',
                     lambda m: m[1] + stamp + m[2], text)
# The JSON field ends with a comma and newline.
if count == 0:
    text, count = re.subn(r'("dateModified": ")[^"]+(")',
                         lambda m: m[1] + stamp + m[2], text)
assert count == 1, f'Expected one dateModified field, got {count}'
text, count = re.subn(r'Last updated [A-Za-z]+ \d{4}\.',
                     f'Last updated {date:%B %Y}.', text)
assert count == 1, f'Expected one footer date, got {count}'
page.write_text(text)
print('Profile modification time:', stamp)
