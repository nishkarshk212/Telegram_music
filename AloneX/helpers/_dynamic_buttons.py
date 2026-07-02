# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic
# ALONE-CODER

import asyncio
import random
from pyrogram.enums import ButtonStyle
from pyrogram import types

from AloneX import app, db, logger


class DynamicButtons:
    """Manages continuously changing button colors for playing messages."""
    
    def __init__(self):
        self.active_tasks = {}  # chat_id -> task
        self.current_colors = {}  # chat_id -> current color index
    
    async def start_color_cycle(self, chat_id: int, message_id: int, original_markup: types.InlineKeyboardMarkup):
        """Start a background task to cycle button colors every 5 seconds."""
        if chat_id in self.active_tasks:
            return  # Already running
        
        self.current_colors[chat_id] = 0
        task = asyncio.create_task(
            self._color_cycle_task(chat_id, message_id, original_markup)
        )
        self.active_tasks[chat_id] = task
    
    async def _color_cycle_task(self, chat_id: int, message_id: int, original_markup: types.InlineKeyboardMarkup):
        """Background task that updates button colors every 5 seconds."""
        colors = [
            ButtonStyle.PRIMARY,
            ButtonStyle.SUCCESS, 
            ButtonStyle.DANGER,
            ButtonStyle.DEFAULT
        ]
        
        try:
            while True:
                await asyncio.sleep(5)
                
                # Check if message still exists and is playing
                if not await db.get_call(chat_id):
                    await self.stop_color_cycle(chat_id)
                    break
                
                # Cycle through colors
                self.current_colors[chat_id] = (self.current_colors[chat_id] + 1) % len(colors)
                current_color = colors[self.current_colors[chat_id]]
                
                # Rebuild markup with new colors
                new_markup = self._rebuild_markup_with_color(original_markup, current_color)
                
                try:
                    await app.edit_message_reply_markup(
                        chat_id=chat_id,
                        message_id=message_id,
                        reply_markup=new_markup
                    )
                except Exception as e:
                    logger.debug(f"[DynamicButtons] Failed to update colors for {chat_id}: {e}")
                    await self.stop_color_cycle(chat_id)
                    break
                    
        except asyncio.CancelledError:
            pass
    
    def _rebuild_markup_with_color(self, markup: types.InlineKeyboardMarkup, color: ButtonStyle) -> types.InlineKeyboardMarkup:
        """Rebuild inline keyboard with specified button color."""
        from AloneX.helpers import buttons
        
        new_rows = []
        for row in markup.inline_keyboard:
            new_row = []
            for btn in row:
                # Skip URL buttons and copy buttons (keep them as is)
                if btn.url or btn.copy_text:
                    new_row.append(btn)
                else:
                    # Apply new color to callback buttons
                    new_row.append(
                        buttons.ikb(
                            text=btn.text,
                            callback_data=btn.callback_data,
                            style=color
                        )
                    )
            new_rows.append(new_row)
        
        return buttons.ikm(new_rows)
    
    async def stop_color_cycle(self, chat_id: int):
        """Stop the color cycle for a chat."""
        if chat_id in self.active_tasks:
            task = self.active_tasks[chat_id]
            if not task.done():
                task.cancel()
            del self.active_tasks[chat_id]
        
        if chat_id in self.current_colors:
            del self.current_colors[chat_id]


# Global instance
dynamic_buttons = DynamicButtons()
