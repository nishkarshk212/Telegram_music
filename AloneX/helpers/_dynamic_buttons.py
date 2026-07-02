# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic
# ALONE-CODER

import asyncio
from pyrogram import types

from AloneX import app, db, logger


class DynamicButtons:
    """Manages continuously changing button emojis for playing messages."""
    
    def __init__(self):
        self.active_tasks = {}  # chat_id -> task
        self.current_emoji_index = {}  # chat_id -> current emoji index
        # Color emojis to cycle through
        self.color_emojis = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "🟤", "⚪", "🌈"]
    
    async def start_color_cycle(self, chat_id: int, message_id: int, original_markup: types.InlineKeyboardMarkup):
        """Start a background task to cycle button emojis every 5 seconds."""
        if chat_id in self.active_tasks:
            return  # Already running
        
        self.current_emoji_index[chat_id] = 0
        task = asyncio.create_task(
            self._color_cycle_task(chat_id, message_id, original_markup)
        )
        self.active_tasks[chat_id] = task
    
    async def _color_cycle_task(self, chat_id: int, message_id: int, original_markup: types.InlineKeyboardMarkup):
        """Background task that updates button emojis every 5 seconds."""
        try:
            while True:
                await asyncio.sleep(5)
                
                # Check if message still exists and is playing
                if not await db.get_call(chat_id):
                    await self.stop_color_cycle(chat_id)
                    break
                
                # Cycle through emojis
                self.current_emoji_index[chat_id] = (self.current_emoji_index[chat_id] + 1) % len(self.color_emojis)
                current_emoji = self.color_emojis[self.current_emoji_index[chat_id]]
                
                # Rebuild markup with new emojis
                new_markup = self._rebuild_markup_with_emoji(original_markup, current_emoji)
                
                try:
                    await app.edit_message_reply_markup(
                        chat_id=chat_id,
                        message_id=message_id,
                        reply_markup=new_markup
                    )
                except Exception as e:
                    logger.debug(f"[DynamicButtons] Failed to update emojis for {chat_id}: {e}")
                    await self.stop_color_cycle(chat_id)
                    break
                    
        except asyncio.CancelledError:
            pass
    
    def _rebuild_markup_with_emoji(self, markup: types.InlineKeyboardMarkup, emoji: str) -> types.InlineKeyboardMarkup:
        """Rebuild inline keyboard with emoji prefix while preserving all properties."""
        new_rows = []
        for row in markup.inline_keyboard:
            new_row = []
            for btn in row:
                # Skip URL buttons and copy buttons (keep them as is)
                if btn.url or btn.copy_text:
                    new_row.append(btn)
                else:
                    # Add emoji prefix to callback button text
                    # Check if text already has an emoji prefix
                    text = btn.text
                    if text and not text[0] in self.color_emojis:
                        # Add emoji prefix for control buttons
                        if any(char in text for char in ['▷', 'II', '⥁', '‣‣I', '▢']):
                            text = f"{emoji} {text}"
                    
                    new_row.append(
                        types.InlineKeyboardButton(
                            text=text,
                            callback_data=btn.callback_data,
                            url=btn.url,
                            switch_inline_query=btn.switch_inline_query,
                            switch_inline_query_current_chat=btn.switch_inline_query_current_chat,
                            callback_game=btn.callback_game,
                            pay=btn.pay,
                            login_url=btn.login_url,
                            web_app=btn.web_app,
                        )
                    )
            new_rows.append(new_row)
        
        return types.InlineKeyboardMarkup(inline_keyboard=new_rows)
    
    async def stop_color_cycle(self, chat_id: int):
        """Stop the color cycle for a chat."""
        if chat_id in self.active_tasks:
            task = self.active_tasks[chat_id]
            if not task.done():
                task.cancel()
            del self.active_tasks[chat_id]
        
        if chat_id in self.current_emoji_index:
            del self.current_emoji_index[chat_id]


# Global instance
dynamic_buttons = DynamicButtons()
