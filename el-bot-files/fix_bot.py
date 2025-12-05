#!/usr/bin/env python3
with open('/home/flomaster/projects/bots/el-bot/bot.py', 'r') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # Check for broken "Repository updated!" string
    if 'reply_text("Repository updated!' in line and not line.rstrip().endswith(')'):
        combined = line.rstrip() + '\\n\\n" + output)\n'
        new_lines.append(combined)
        i += 3  # Skip broken lines
        continue
    # Check for broken "Update failed:" string
    elif 'reply_text("Update failed:' in line and not line.rstrip().endswith(')'):
        combined = line.rstrip() + '\\n" + errors[:500])\n'
        new_lines.append(combined)
        i += 2
        continue
    new_lines.append(line)
    i += 1

with open('/home/flomaster/projects/bots/el-bot/bot.py', 'w') as f:
    f.writelines(new_lines)
print('Fixed broken strings')
