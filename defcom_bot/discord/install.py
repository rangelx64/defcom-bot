from __future__ import annotations

import discord
from discord import ui

from ..database import database

ROLE_FIELDS = {
    "role.global_leader": "Cargo de líder global",
    "role.squad_leader": "Cargo de líder de pelotão",
    "staff_roles": "Cargos autorizados para staff",
    "role.candidate": "Cargo de candidato",
    "role.approved_member": "Cargo de membro aprovado / operador",
    "role.community": "Cargo de comunidade",
    "role.pc": "Cargo da plataforma PC",
    "role.console": "Cargo da plataforma Console",
    "role.platoon.alfa": "Cargo do pelotão Alfa",
    "role.platoon.bravo": "Cargo do pelotão Bravo",
    "role.platoon.charlie": "Cargo do pelotão Charlie",
    "role.platoon.delta": "Cargo do pelotão Delta",
}

CHANNEL_FIELDS = {
    "channel.welcome": "Canal de boas-vindas",
    "channel.apply": "Canal da página de candidatura",
    "channel.candidates": "Canal privado de candidaturas para staff",
    "channel.general": "Canal geral",
    "channel.media": "Canal de mídia",
    "channel.loadout": "Canal de loadouts",
    "channel.warning": "Canal de avisos e regras",
    "channel.arts": "Canal de artes",
    "channel.announcements": "Canal de comunicados",
    "channel.aph": "Canal de guia rápido de combate / APH",
}


def _config_label(guild: discord.Guild, key: str, label: str) -> str:
    value = database.get_guild_config(guild.id, key)
    if value is None:
        return f"{label}: não configurado"
    values = value if isinstance(value, list) else [value]
    mentions = []
    for item in values:
        identifier = int(item)
        entity = guild.get_role(identifier) if key in ROLE_FIELDS else guild.get_channel(identifier)
        mentions.append(entity.mention if entity else f"ID inválido ({identifier})")
    return f"{label}: {', '.join(mentions) if mentions else 'não configurado'}"


def install_embed(guild: discord.Guild) -> discord.Embed:
    missing = [key for key in (*ROLE_FIELDS, *CHANNEL_FIELDS)
               if database.get_guild_config(guild.id, key) is None]
    embed = discord.Embed(
        title="Configuração inicial do bot",
        description=(
            "Selecione cada função e associe o cargo ou canal correspondente. "
            "Os IDs são gravados no SQLite. O dono do servidor é reconhecido "
            "pelo próprio Discord e não precisa de cargo. "
            f"Configuração preenchida: {len(ROLE_FIELDS) + len(CHANNEL_FIELDS) - len(missing)}/"
            f"{len(ROLE_FIELDS) + len(CHANNEL_FIELDS)} seleções."
        ),
        color=discord.Color.blurple(),
    )
    roles = "\n".join(_config_label(guild, key, label) for key, label in ROLE_FIELDS.items())
    channels = "\n".join(_config_label(guild, key, label) for key, label in CHANNEL_FIELDS.items())
    embed.add_field(name="Cargos", value=roles[:1024], inline=False)
    embed.add_field(name="Canais", value=channels[:1024], inline=False)
    embed.set_footer(text="Somente o dono do servidor pode configurar ou alterar estes IDs.")
    return embed


class InstallView(ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=900)
        self.owner_id = owner_id
        self.add_item(InstallFieldSelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id or interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                "Somente o dono do servidor pode usar esta configuração.", ephemeral=True,
            )
            return False
        return True


class InstallFieldSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=label, value=key, description="Cargo do servidor")
            for key, label in ROLE_FIELDS.items()
        ] + [
            discord.SelectOption(label=label, value=key, description="Canal do servidor")
            for key, label in CHANNEL_FIELDS.items()
        ]
        super().__init__(placeholder="Escolha uma função para configurar", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        label = ROLE_FIELDS.get(key) or CHANNEL_FIELDS[key]
        await interaction.response.edit_message(
            content=f"Selecione o item para **{label}**.",
            embed=None,
            view=InstallEntityView(self.view.owner_id, key),
        )


class InstallEntityView(ui.View):
    def __init__(self, owner_id: int, key: str):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.key = key
        if key in ROLE_FIELDS:
            max_values = 25 if key == "staff_roles" else 1
            self.add_item(RoleValueSelect(key, max_values=max_values))
        else:
            self.add_item(ChannelValueSelect(key))
        self.add_item(ClearValueButton())
        self.add_item(BackToInstallButton())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id or interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                "Somente o dono do servidor pode usar esta configuração.", ephemeral=True,
            )
            return False
        return True


class RoleValueSelect(ui.RoleSelect):
    def __init__(self, key: str, *, max_values: int):
        super().__init__(placeholder="Selecione o cargo pelo menu", min_values=1, max_values=max_values)
        self.key = key

    async def callback(self, interaction: discord.Interaction):
        if any(role.is_default() or role.managed for role in self.values):
            return await interaction.response.send_message(
                "Não use @everyone nem cargos gerenciados por integração nesta configuração.", ephemeral=True,
            )
        role_ids = [str(role.id) for role in self.values]
        value = role_ids if self.key == "staff_roles" else role_ids[0]
        database.set_guild_config(interaction.guild_id, self.key, value)
        await interaction.response.edit_message(
            content="Cargo salvo no SQLite.", embed=install_embed(interaction.guild),
            view=InstallView(interaction.user.id),
        )


class ChannelValueSelect(ui.ChannelSelect):
    def __init__(self, key: str):
        channel_types = [discord.ChannelType.text, discord.ChannelType.news]
        super().__init__(placeholder="Selecione o canal pelo menu", min_values=1, max_values=1,
                         channel_types=channel_types)
        self.key = key

    async def callback(self, interaction: discord.Interaction):
        channel = self.values[0]
        database.set_guild_config(interaction.guild_id, self.key, str(channel.id))
        await interaction.response.edit_message(
            content="Canal salvo no SQLite.", embed=install_embed(interaction.guild),
            view=InstallView(interaction.user.id),
        )


class ClearValueButton(ui.Button):
    def __init__(self):
        super().__init__(label="Limpar configuração", style=discord.ButtonStyle.danger, row=1)

    async def callback(self, interaction: discord.Interaction):
        view: InstallEntityView = self.view
        database.delete_guild_config(interaction.guild_id, view.key)
        await interaction.response.edit_message(
            content="Configuração removida do SQLite.", embed=install_embed(interaction.guild),
            view=InstallView(interaction.user.id),
        )


class BackToInstallButton(ui.Button):
    def __init__(self):
        super().__init__(label="Voltar", style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=None, embed=install_embed(interaction.guild),
            view=InstallView(interaction.user.id),
        )
