from __future__ import annotations

import re
import discord
from discord import ui

from .channels import find_channel
from .names import normalize_name


def hex_to_int(value: str | None, fallback: int = 0x2B2D31) -> int:
    try:
        return int(str(value or "").replace("#", ""), 16)
    except ValueError:
        return fallback


def text(content: str) -> ui.TextDisplay:
    return ui.TextDisplay(content)


def separator(visible: bool = True) -> ui.Separator:
    return ui.Separator(visible=visible, spacing=discord.SeparatorSpacing.large)


def mention(guild: discord.Guild, name: str) -> str:
    channel = find_channel(guild, name)
    return channel.mention if channel else f"#{normalize_name(name)}"


def channel_url(guild: discord.Guild, name: str) -> str | None:
    channel = find_channel(guild, name)
    return channel.jump_url if channel else None


def resolve_mentions(guild: discord.Guild, content: str) -> str:
    def replace(match):
        channel = find_channel(guild, match.group(1))
        return channel.mention if channel else match.group(0)
    return re.sub(r"#([a-z0-9][a-z0-9-]*)", replace, str(content), flags=re.I)


class ConfirmationView(ui.View):
    def __init__(self, owner_id: int, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.confirmed = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Somente quem iniciou a ação pode confirmar.", ephemeral=True)
            return False
        return True

    @ui.button(label="Confirmar", style=discord.ButtonStyle.danger, custom_id="confirm:yes")
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        self.confirmed = True
        self.stop()
        await interaction.response.edit_message(content=f"{interaction.message.content}\n\n✅ Confirmado.", view=None)

    @ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, custom_id="confirm:no")
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        self.confirmed = False
        self.stop()
        await interaction.response.edit_message(content=f"{interaction.message.content}\n\n❌ Cancelado.", view=None)


async def confirm_action(interaction: discord.Interaction, *, title: str, description: str = "",
                         confirm_label: str = "Confirmar", timeout: float = 60) -> bool:
    view = ConfirmationView(interaction.user.id, timeout)
    next(item for item in view.children if isinstance(item, ui.Button) and item.custom_id == "confirm:yes").label = confirm_label
    message = f"**{title}**\n{description}" if description else f"**{title}**"
    confirmation_message = await interaction.followup.send(message, view=view, ephemeral=True, wait=True)
    timed_out = await view.wait()
    if timed_out:
        await confirmation_message.edit(content=f"{message}\n\n⌛ Tempo esgotado. Ação cancelada.", view=None)
        return False
    return view.confirmed
