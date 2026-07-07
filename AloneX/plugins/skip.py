# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic


from pyrogram import filters, types

from AloneX import anon, app, db, lang, logger
from AloneX.helpers import can_skip


@app.on_message(filters.command(["skip", "next"]) & filters.group & ~app.bl_users)
@lang.language()
@can_skip
async def _skip(_, m: types.Message):
    logger.info(f"[skip] Skip command called by user {m.from_user.id} in chat {m.chat.id}")
    if not await db.get_call(m.chat.id):
        logger.info(f"[skip] No active call in chat {m.chat.id}")
        return await m.reply_text(m.lang["not_playing"])

    logger.info(f"[skip] Calling play_next for chat {m.chat.id}")
    try:
        await anon.play_next(m.chat.id)
        await m.reply_text(m.lang["play_skipped"].format(m.from_user.mention))
    except Exception as e:
        logger.error(f"[skip] Error during skip: {type(e).__name__} - {e}")
        import traceback
        logger.error(f"[skip] Traceback: {traceback.format_exc()}")
