# ALONE-CODER
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ButtonStyle

def settings_markup(lang, admin, delete, pmsg_delete, skip, chat_id):
    buttons = [
        [
            InlineKeyboardButton(
                text="Enabled" if admin else "Disabled",
                callback_data=f"settings play {chat_id}",
                style=ButtonStyle.SUCCESS if admin else ButtonStyle.DANGER,
            ),
        ],
        [
            InlineKeyboardButton(
                text="Enabled" if delete else "Disabled",
                callback_data=f"settings delete {chat_id}",
                style=ButtonStyle.SUCCESS if delete else ButtonStyle.DANGER,
            ),
            InlineKeyboardButton(
                text="Enabled" if pmsg_delete else "Disabled",
                callback_data=f"settings pmsg_delete {chat_id}",
                style=ButtonStyle.SUCCESS if pmsg_delete else ButtonStyle.DANGER,
            ),
        ],
        [
            InlineKeyboardButton(
                text="Enabled" if skip else "Disabled",
                callback_data=f"settings skip {chat_id}",
                style=ButtonStyle.SUCCESS if skip else ButtonStyle.DANGER,
            ),
        ],
        [
            InlineKeyboardButton(
                text=lang.get("close", "⌯ Close ⌯"),
                callback_data="help close",
            ),
        ],
    ]
    return InlineKeyboardMarkup(buttons)
