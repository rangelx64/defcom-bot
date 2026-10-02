from __future__ import annotations

import discord

from ..database import database


def configured_role(guild: discord.Guild, key: str) -> discord.Role | None:
    value = database.get_guild_config(guild.id, key)
    if value is None or isinstance(value, list):
        return None
    try:
        return guild.get_role(int(value))
    except (TypeError, ValueError):
        return None


def configured_roles(guild: discord.Guild, key: str) -> list[discord.Role]:
    value = database.get_guild_config(guild.id, key, [])
    if not isinstance(value, list):
        value = [value]
    roles = []
    for identifier in value:
        try:
            role = guild.get_role(int(identifier))
        except (TypeError, ValueError):
            role = None
        if role:
            roles.append(role)
    return roles


def configured_channel(guild: discord.Guild, key: str):
    value = database.get_guild_config(guild.id, key)
    if value is None or isinstance(value, list):
        return None
    try:
        return guild.get_channel(int(value))
    except (TypeError, ValueError):
        return None
