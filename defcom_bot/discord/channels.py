from __future__ import annotations

import discord

from ..database import database
from ..log import get_logger
from .names import normalize_name

log = get_logger(__name__)


def find_category(guild: discord.Guild, name: str) -> discord.CategoryChannel | None:
    return discord.utils.get(guild.categories, name=normalize_name(name))


def find_channel(guild: discord.Guild, name: str, category: discord.CategoryChannel | None = None):
    wanted = normalize_name(name)
    for channel in guild.channels:
        if isinstance(channel, discord.CategoryChannel) or channel.name != wanted:
            continue
        if category is None or channel.category_id == category.id:
            return channel
    return None


async def create_category(guild: discord.Guild, name: str) -> tuple[bool, discord.CategoryChannel]:
    existing = find_category(guild, name)
    if existing:
        return False, existing
    channel = await guild.create_category(normalize_name(name))
    log.info("categoria criada: %s", channel.name)
    return True, channel


def build_overwrites(guild: discord.Guild, preset: str, *, kind: str, roles=(), staff_roles=None):
    staff_roles = database.get_guild_config(guild.id, "staff_roles", []) if staff_roles is None else staff_roles
    role_map = {role.name: role for role in guild.roles}
    staff = []
    for role_id in staff_roles:
        try:
            role = guild.get_role(int(role_id))
        except (TypeError, ValueError):
            role = None
        if role:
            staff.append(role)
    extras = [role_map[name] for name in roles if name in role_map]
    read = discord.PermissionOverwrite(view_channel=True)
    write = discord.PermissionOverwrite(view_channel=True)
    if kind == "voice":
        write.connect = write.speak = True
        read.connect = read.speak = False
    else:
        write.send_messages = True
        read.send_messages = False
    result = {}
    if preset == "publico":
        result[guild.default_role] = write
    elif preset == "leitura":
        result[guild.default_role] = read
        result.update({role: write for role in (*staff, *extras)})
    elif preset in {"staff", "privado"}:
        result[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
        selected = staff if preset == "staff" else [*staff, *extras]
        result.update({role: write for role in selected})
    else:
        result[guild.default_role] = write
    return result


async def create_channel(guild: discord.Guild, *, name: str, type: str = "text", category_name: str | None = None,
                         preset: str = "publico", roles=(), topic: str | None = None):
    parent = find_category(guild, category_name) if category_name else None
    if category_name and parent is None:
        raise ValueError(f'Categoria "{category_name}" não existe. Crie a categoria primeiro.')
    overwrites = build_overwrites(guild, preset, kind=type, roles=roles)
    if type == "voice":
        channel = await guild.create_voice_channel(normalize_name(name), category=parent, overwrites=overwrites)
    else:
        channel = await guild.create_text_channel(normalize_name(name), category=parent, overwrites=overwrites, topic=topic)
    log.info("canal criado: %s (%s)", channel.name, type)
    return channel


async def rename_channel(guild: discord.Guild, name: str, new_name: str):
    channel = find_channel(guild, name)
    if not channel:
        raise ValueError(f'Canal "{name}" não encontrado.')
    await channel.edit(name=normalize_name(new_name))
    return channel


async def move_channel(guild: discord.Guild, name: str, category_name: str | None):
    channel = find_channel(guild, name)
    parent = find_category(guild, category_name) if category_name else None
    if not channel:
        raise ValueError(f'Canal "{name}" não encontrado.')
    if category_name and not parent:
        raise ValueError(f'Categoria "{category_name}" não existe.')
    await channel.edit(category=parent, sync_permissions=False)
    return channel


async def delete_channel(guild: discord.Guild, name: str):
    channel = find_channel(guild, name)
    if not channel:
        raise ValueError(f'Canal "{name}" não encontrado.')
    await channel.delete()


async def delete_category(guild: discord.Guild, name: str) -> int:
    category = find_category(guild, name)
    if not category:
        raise ValueError(f'Categoria "{name}" não encontrada.')
    children = len(category.channels)
    await category.delete()
    return children
