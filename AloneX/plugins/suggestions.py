# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic
# ALONE-CODER

import asyncio
import re

from py_yt import VideosSearch
from pyrogram import filters, types

from AloneX import app, db, lang, queue, yt, xbit
from AloneX.helpers import Track, buttons


# ── Colour palette for suggestion buttons (vibrant rainbow colors) ───────────────
# Pyrogram InlineKeyboardButton supports callback_data only; visual colour
# is achieved via emoji prefixes so they look vibrant in Telegram.
_BTN_EMOJIS = ["🔴", "🟠", "�", "�🟢", "�", "🟣", "🟤", "⚪", "�", "💎", "✨", "�"]


def _clean_title(title: str) -> str:
    """Strip emojis, special symbols; keep only the song name."""
    title = re.sub(r"[^\w\s\-\'\(\)\|,&]", "", title, flags=re.UNICODE)
    title = re.sub(r"\s+", " ", title).strip()
    return title[:40]


async def get_suggestions(current_title: str, limit: int = 5) -> list[dict]:
    """
    Search YouTube for songs related to *current_title* and return up to
    *limit* results that are different from the current song.
    """
    try:
        search = VideosSearch(current_title, limit=limit + 3)
        results = (await search.next()).get("result", [])

        suggestions = []
        current_lower = current_title.lower()

        for video in results:
            title = video.get("title", "").strip()
            vid_id = video.get("id", "")
            link = video.get("link", "")
            duration = video.get("duration", "N/A")
            channel = video.get("channel", {}).get("name", "")

            if not vid_id or not title:
                continue

            # Skip if it's the same song (fuzzy match)
            if title.lower() == current_lower:
                continue
            if current_lower in title.lower() and len(title) < len(current_title) + 10:
                continue

            suggestions.append(
                {
                    "id": vid_id,
                    "title": title,
                    "link": link,
                    "duration": duration,
                    "channel": channel,
                }
            )
            if len(suggestions) >= limit:
                break

        return suggestions
    except Exception as e:
        print(f"[suggestions] Error fetching suggestions: {e}")
        return []


async def send_suggestions(chat_id: int, current_title: str) -> None:
    """
    Fetch related songs and send a suggestion message to the chat.
    Each suggestion is an inline button; clicking it adds the song to queue.
    """
    suggestions = await get_suggestions(current_title)
    if not suggestions:
        return

    # Build one button per suggestion, each on its own row
    keyboard_rows = []
    for i, s in enumerate(suggestions):
        emoji = _BTN_EMOJIS[i % len(_BTN_EMOJIS)]
        clean = _clean_title(s["title"])
        btn_text = f"{emoji}  {clean}"
        # callback_data: "suggest_queue <vid_id> <chat_id>"
        cb_data = f"suggest_queue {s['id']} {chat_id}"
        keyboard_rows.append([buttons.ikb(text=btn_text, callback_data=cb_data)])

    markup = buttons.ikm(keyboard_rows)

    text = (
        f"🎵 <b>You might also like:</b>\n"
        f"<i>Tap a song to add it to the queue</i>"
    )

    try:
        await app.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=markup,
            disable_web_page_preview=True,
        )
    except Exception as e:
        print(f"[suggestions] Failed to send suggestions to {chat_id}: {e}")


# ── Callback handler: user clicks a suggestion button ───────────────────────

@app.on_callback_query(filters.regex(r"^suggest_queue") & ~app.bl_users)
@lang.language()
async def suggest_queue_cb(_, query: types.CallbackQuery) -> None:
    """Add the suggested song to the queue when its button is clicked."""
    parts = query.data.split()
    if len(parts) < 3:
        return await query.answer("Invalid request.", show_alert=True)

    vid_id = parts[1]
    chat_id = int(parts[2])
    user = query.from_user.mention

    await query.answer("⏳ Adding to queue...", show_alert=False)

    # Check queue limit
    from AloneX import config
    if len(queue.get_queue(chat_id)) >= config.QUEUE_LIMIT:
        return await query.answer(
            query.lang["play_queue_full"].format(config.QUEUE_LIMIT),
            show_alert=True,
        )

    try:
        # Search by YouTube URL directly
        yt_url = f"https://www.youtube.com/watch?v={vid_id}"
        track = await yt.search(yt_url, 0, video=False)

        if not track:
            return await query.answer("❌ Could not fetch song info.", show_alert=True)

        track.user = user
        track.user_id = query.from_user.id

        position = queue.add(chat_id, track)

        # Update the suggestion message: disable the clicked button visually
        try:
            # Rebuild the keyboard with the clicked button checked
            old_markup = query.message.reply_markup
            new_rows = []
            for row in old_markup.inline_keyboard:
                new_row = []
                for btn in row:
                    if btn.callback_data == query.data:
                        # Mark it as added — strip emoji prefix, add ✔
                        new_text = re.sub(r"^[^\w]+\s*", "", btn.text).strip()
                        new_row.append(
                            buttons.ikb(
                                text=f"✔️  {new_text}",
                                callback_data="suggest_done",
                            )
                        )
                    else:
                        new_row.append(btn)
                new_rows.append(new_row)

            await query.edit_message_reply_markup(
                reply_markup=buttons.ikm(new_rows)
            )
        except Exception:
            pass

        if position == 0 and not await db.get_call(chat_id):
            # Nothing playing – start playback
            from AloneX import anon
            msg = await app.send_message(
                chat_id=chat_id,
                text=query.lang["play_next"],
            )
            if not track.file_path:
                track.file_path = await xbit.download(vid_id, video=False)
            track.message_id = msg.id
            await anon.play_media(chat_id, msg, track)
        else:
            await app.send_message(
                chat_id=chat_id,
                text=query.lang["play_queued"].format(
                    position,
                    track.url,
                    track.title,
                    track.duration,
                    user,
                ),
                disable_web_page_preview=True,
            )

    except Exception as e:
        print(f"[suggest_queue_cb] Error: {e}")
        await query.answer("❌ Something went wrong.", show_alert=True)


# ── Dummy handler for already-added buttons ──────────────────────────────────

@app.on_callback_query(filters.regex(r"^suggest_done") & ~app.bl_users)
async def suggest_done_cb(_, query: types.CallbackQuery) -> None:
    await query.answer("✔️ Already added to queue!", show_alert=False)
