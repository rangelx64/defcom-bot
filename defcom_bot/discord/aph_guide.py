from __future__ import annotations

import discord

from ..content import APH_GUIDE
from .presentation import card


def build_aph_guide_embed() -> discord.Embed:
    embed = card(
        APH_GUIDE["title"], APH_GUIDE["description"], tone="brand",
        footer=APH_GUIDE["footer"],
    )
    embed.color = discord.Color.from_rgb(139, 26, 26)
    for section in APH_GUIDE["sections"]:
        embed.add_field(name=section["name"], value=section["value"], inline=False)
    return embed
