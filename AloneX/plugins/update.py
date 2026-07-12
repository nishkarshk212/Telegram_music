# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic
#ALONE-CODER

import os
import sys
import asyncio

from pyrogram import filters, types

from AloneX import app, config, stop


@app.on_message(filters.command(["update"]) & app.sudoers)
async def _update(_, m: types.Message):
    # Owner only: git pull + auto restart
    if m.from_user.id != config.OWNER_ID:
        return await m.reply_text("This command is restricted to the bot owner.")

    sent = await m.reply_text("Updating from git repository...")

    proc = await asyncio.create_subprocess_shell(
        "git fetch origin && git reset --hard origin/main",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()

    if proc.returncode != 0:
        return await sent.edit_text(
            f"Git update failed (exit {proc.returncode}):\n"
            f"{(err or out).decode(errors='replace')[:1500]}"
        )

    summary = out.decode(errors="replace").strip().splitlines()[-3:]
    await sent.edit_text(
        "Updated from git:\n" + "\n".join(summary) + "\n\nRestarting bot..."
    )

    asyncio.create_task(stop())
    await asyncio.sleep(2)
    os.execl(sys.executable, sys.executable, "-m", "AloneX")
