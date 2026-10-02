from __future__ import annotations

import discord
from discord import ui

from ..content import APH_GUIDE


def build_aph_guide_view() -> ui.LayoutView:
    view = ui.LayoutView(timeout=None)
    blocks = [ui.TextDisplay(f"# {APH_GUIDE['title']}\n{APH_GUIDE['description']}")]
    blocks.extend(
        ui.TextDisplay(f"## {section['name']}\n{section['value']}")
        for section in APH_GUIDE["sections"]
    )
    blocks[-1].content += f"\n\n-# {APH_GUIDE['footer']}"
    view.add_item(ui.Container(*blocks, accent_color=discord.Color.from_rgb(139, 26, 26)))
    return view
