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


def role_assignment_issue(guild: discord.Guild, role: discord.Role) -> str | None:
    """Explain why Discord will reject assigning this role to a member."""
    bot_member = guild.me
    if bot_member is None:
        return "não consegui localizar o membro do bot nesta guild"
    if not bot_member.guild_permissions.manage_roles:
        return "o bot não tem a permissão Gerenciar Cargos"
    if not role.is_assignable():
        return (
            f"o cargo {role.mention} (ID {role.id}) está acima/igual ao cargo mais alto do bot, "
            "ou é um cargo gerenciado e não pode ser atribuído por ele"
        )
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
