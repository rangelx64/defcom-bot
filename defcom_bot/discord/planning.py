from __future__ import annotations

import asyncio
from datetime import timedelta
import discord

from ..content import DESIRED
from ..log import get_logger
from ..models import ApplyResults, PlannedAction
from .channels import create_category, create_channel, find_category
from .names import normalize_name

log = get_logger(__name__)


def load_desired() -> dict:
    return DESIRED


def build_plan(guild: discord.Guild, desired: dict) -> list[PlannedAction]:
    actions = []
    for category in desired.get("categories", []):
        name = normalize_name(category["name"])
        existing = find_category(guild, name)
        if not existing:
            actions.append(PlannedAction("create_category", name))
        for channel in category.get("channels", []):
            channel_name = normalize_name(channel["name"])
            parent = existing or find_category(guild, name)
            exists = any(child.name == channel_name for child in parent.channels) if parent else any(
                not isinstance(item, discord.CategoryChannel) and item.category_id is None and item.name == channel_name
                for item in guild.channels)
            if not exists:
                actions.append(PlannedAction("create_channel", channel_name,
                    "voice" if channel.get("type") == "voice" else "text", name,
                    channel.get("preset", "publico"), tuple(channel.get("roles", []))))
    return actions


def render_plan(actions: list[PlannedAction]) -> str:
    if not actions:
        return "✅ Nada a fazer. O servidor já atende à estrutura definida no código."
    lines = ["**Plano: somente criação. Nada será alterado ou removido.**", ""]
    for action in actions:
        if action.op == "create_category":
            lines.append(f"• ➕ Categoria `{action.name}`")
        else:
            icon = "🔊" if action.type == "voice" else "💬"
            lines.append(f"• ➕ {icon} `{action.category}/{action.name}` (preset: {action.preset})")
    return "\n".join([*lines, "", f"Total: **{len(actions)}** item(ns) a criar."])


async def apply_plan(guild: discord.Guild, actions: list[PlannedAction]) -> ApplyResults:
    result = ApplyResults()
    for action in actions:
        try:
            if action.op == "create_category":
                created, _ = await create_category(guild, action.name)
                result.created += int(created)
            elif action.op == "create_channel":
                await create_channel(guild, name=action.name, type=action.type or "text",
                    category_name=action.category, preset=action.preset, roles=action.roles)
                result.created += 1
        except Exception as error:
            log.exception("falha ao aplicar %s %s", action.op, action.name)
            result.failed.append({"action": action.as_dict(), "error": str(error)})
        await asyncio.sleep(0.3)
    return result
