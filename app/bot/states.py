from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AdminFlow(StatesGroup):
    waiting_broadcast_message = State()
    waiting_access_user_id = State()
    waiting_remove_access_user_id = State()
    waiting_custom_text_key = State()
    waiting_custom_text_value = State()
    waiting_custom_button_key = State()
    waiting_custom_button_value = State()
    confirm_delete_step_1 = State()
    confirm_delete_step_2 = State()
