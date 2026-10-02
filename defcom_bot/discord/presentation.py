from __future__ import annotations

import discord


COLORS = {
    "brand": 0x2B2D31,
    "success": 0x238636,
    "info": 0x356AE6,
    "warning": 0xD79B18,
    "error": 0xC83C3C,
}
BRAND_NAME = "DEFCOM | Central de Operações"
BRAND_FOOTER = "DEFCOM • Sistema de apoio"


def card(
    title: str,
    description: str | None = None,
    *,
    tone: str = "info",
    footer: str = BRAND_FOOTER,
    timestamp: bool = False,
) -> discord.Embed:
    """Build a consistent, readable DEFCOM embed for bot messages."""
    body = description or ""
    if len(body) > 4096:
        body = body[:4078].rstrip() + "…\n[Conteúdo resumido]"
    embed = discord.Embed(
        title=title[:256],
        description=(body or None),
        color=COLORS.get(tone, COLORS["info"]),
        timestamp=discord.utils.utcnow() if timestamp else None,
    )
    embed.set_author(name=BRAND_NAME)
    embed.set_footer(text=footer[:2048])
    return embed


def confirmation(title: str, description: str) -> discord.Embed:
    return card(title, description, tone="warning", footer="DEFCOM • Confirme a ação antes de continuar")


def result(title: str, description: str, *, success: bool = True) -> discord.Embed:
    return card(title, description, tone="success" if success else "error")
