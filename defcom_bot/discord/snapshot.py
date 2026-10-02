from __future__ import annotations

from datetime import timezone
import discord


def overwrites_data(guild: discord.Guild, channel) -> dict:
    out = {}
    for target, overwrite in channel.overwrites.items():
        is_role = isinstance(target, discord.Role)
        out[target.name if is_role else str(target)] = {
            "type": "role" if is_role else "member", "id": str(target.id),
            "allow": [name for name, value in overwrite if value is True],
            "deny": [name for name, value in overwrite if value is False],
        }
    return out


def channel_data(guild: discord.Guild, channel) -> dict:
    kind = ("category" if isinstance(channel, discord.CategoryChannel) else
            "text" if isinstance(channel, discord.TextChannel) else
            "voice" if isinstance(channel, discord.VoiceChannel) else str(channel.type).lower())
    return {"id": str(channel.id), "name": channel.name, "type": kind, "position": channel.position,
            "parent": channel.category.name if channel.category else None,
            "parentId": str(channel.category_id) if channel.category_id else None,
            "topic": getattr(channel, "topic", None), "nsfw": getattr(channel, "nsfw", None),
            "overwrites": overwrites_data(guild, channel)}


def build_snapshot(guild: discord.Guild) -> dict:
    categories = [{"id": str(cat.id), "name": cat.name, "position": cat.position,
                   "overwrites": overwrites_data(guild, cat),
                   "channels": [channel_data(guild, ch) for ch in sorted(cat.channels, key=lambda c: c.position)]}
                  for cat in sorted(guild.categories, key=lambda c: c.position)]
    uncategorized = [channel_data(guild, channel) for channel in sorted(guild.channels, key=lambda c: c.position)
                     if not isinstance(channel, discord.CategoryChannel) and channel.category_id is None]
    roles = [{"id": str(role.id), "name": role.name, "color": f"#{role.color.value:06x}", "position": role.position,
              "hoist": role.hoist, "mentionable": role.mentionable, "managed": role.managed,
              "permissions": [name for name, value in role.permissions if value]}
             for role in sorted(guild.roles, key=lambda item: item.position, reverse=True)]
    created = guild.created_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return {"generatedAt": discord.utils.utcnow().isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "guild": {"id": str(guild.id), "name": guild.name, "description": guild.description,
                      "memberCount": guild.member_count, "createdAt": created},
            "categories": categories, "uncategorized": uncategorized, "roles": roles}
