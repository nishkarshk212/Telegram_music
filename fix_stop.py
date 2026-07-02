#!/usr/bin/env python3

with open('AloneX/core/calls.py', 'r') as f:
    lines = f.readlines()

# Find the stop method and fix it
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    new_lines.append(line)
    
    # Check if this is the stop method's except block
    if i > 0 and 'except:' in line and 'await db.remove_call(chat_id)' in lines[i-2]:
        # Add the missing code
        new_lines.append('\n')
        new_lines.append('        # Stop dynamic color cycling\n')
        new_lines.append('        await dynamic_buttons.stop_color_cycle(chat_id)\n')
        new_lines.append('\n')
        new_lines.append('        try: \n')
        new_lines.append('            await client.leave_call(chat_id, close=False) \n')
        new_lines.append('        except: \n')
        new_lines.append('            pass\n')
        new_lines.append('\n')
        new_lines.append('        # Send suggestions after all songs are played\n')
        new_lines.append('        try:\n')
        new_lines.append('            from AloneX.plugins.suggestions import send_suggestions\n')
        new_lines.append('            import asyncio as _asyncio\n')
        new_lines.append('            _asyncio.create_task(send_suggestions(chat_id, "Popular Songs"))\n')
        new_lines.append('        except Exception:\n')
        new_lines.append('            pass\n')
        new_lines.append('\n')
    
    i += 1

with open('AloneX/core/calls.py', 'w') as f:
    f.writelines(new_lines)

print("Fixed stop method")
