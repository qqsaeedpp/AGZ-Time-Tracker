from __future__ import annotations

from app.config import settings
from app.database import repositories as repo
from app.database.db import session_factory
from app.database.models import User


def is_owner_id(telegram_id: int) -> bool:
    return telegram_id in settings.owner_ids


async def get_or_create_user(
    telegram_id: int, username: str | None, first_name: str | None
) -> User:
    """Fetch a user, creating it on first contact. Owner flags are kept in sync
    with OWNER_IDS from the environment on every call."""
    owner = is_owner_id(telegram_id)
    async with session_factory() as session:
        async with session.begin():
            user = await repo.get_user_by_telegram_id(session, telegram_id)
            if user is None:
                user = await repo.create_user(
                    session,
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    is_owner=owner,
                    is_allowed=owner,
                )
            else:
                changed = False
                if user.username != username:
                    user.username, changed = username, True
                if user.first_name != first_name:
                    user.first_name, changed = first_name, True
                if user.is_owner != owner:
                    user.is_owner = owner
                    if owner:
                        user.is_allowed = True
                    changed = True
                if changed:
                    await session.flush()
            session.expunge(user)
            return user


async def grant_access(telegram_id: int) -> bool:
    async with session_factory() as session:
        async with session.begin():
            user = await repo.get_user_by_telegram_id(session, telegram_id)
            if user is None:
                user = await repo.create_user(
                    session,
                    telegram_id=telegram_id,
                    username=None,
                    first_name=None,
                    is_owner=is_owner_id(telegram_id),
                    is_allowed=True,
                )
            else:
                user.is_allowed = True
                await session.flush()
    return True


async def revoke_access(telegram_id: int) -> bool:
    async with session_factory() as session:
        async with session.begin():
            user = await repo.set_user_allowed(session, telegram_id, False)
            return user is not None


async def list_allowed_users() -> list[User]:
    async with session_factory() as session:
        users = await repo.list_allowed_users(session)
        for user in users:
            session.expunge(user)
        return users
