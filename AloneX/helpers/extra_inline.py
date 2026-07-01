# ALONE-CODER
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ButtonStyle

def settings_markup(lang, admin, delete, pmsg_delete, skip, chat_id):
    buttons = [
        [
            InlineKeyboardButton(
                text=lang.get("play_mode", "Admin Only Play") + (" : Enabled" if admin else " : Disabled"),
                callback_data=f"settings play {chat_id}",
                style=ButtonStyle.SUCCESS if admin else ButtonStyle.DANGER,
            ),
        ],
        [
            InlineKeyboardButton(
                text=lang.get("cmd_delete", "Command Delete") + (" : Enabled" if delete else " : Disabled"),
                callback_data=f"settings delete {chat_id}",
                style=ButtonStyle.SUCCESS if delete else ButtonStyle.DANGER,
            ),
            InlineKeyboardButton(
                text=("P-Msg Delete: Enabled" if pmsg_delete else "P-Msg Delete: Disabled"),
                callback_data=f"settings pmsg_delete {chat_id}",
                style=ButtonStyle.SUCCESS if pmsg_delete else ButtonStyle.DANGER,
            ),
        ],
        [
            InlineKeyboardButton(
                text=lang.get("skip_mode", "Skip Permission") + (" : Enabled" if skip else " : Disabled"),
                callback_data=f"settings skip {chat_id}",
                style=ButtonStyle.SUCCESS if skip else ButtonStyle.DANGER,
            ),
        ],
        [
            InlineKeyboardButton(
                text=lang.get("close", "⌯ Close ⌯"),
                callback_data="help close",
                style=ButtonStyle.PRIMARY,
            ),
        ],
    ]
    return InlineKeyboardMarkup(buttons)
