from __future__ import annotations

import discord
from ..log import get_logger

from .server_config import configured_channel, configured_role, role_assignment_issue

log = get_logger(__name__)

JOIN_CHANNEL_KEYS = (
    "channel.apply", "channel.warning", "channel.general", "channel.media",
)


def _is_chat(channel: discord.abc.GuildChannel) -> bool:
    return isinstance(channel, (discord.TextChannel, discord.ForumChannel, discord.VoiceChannel, discord.StageChannel))


def _leadership_roles(guild: discord.Guild) -> list[discord.Role]:
    return [
        role for key in ("role.global_leader", "role.squad_leader")
        if (role := configured_role(guild, key)) is not None
    ]


def _is_leadership_only(entity: discord.abc.GuildChannel, leader_roles: list[discord.Role]) -> bool:
    """Recognize existing private rooms from their current configured role overwrites."""
    candidates = [entity]
    category = getattr(entity, "category", None)
    if category is not None:
        candidates.append(category)
    for target in candidates:
        if target.overwrites_for(entity.guild.default_role).view_channel is not False:
            continue
        if any(target.overwrites_for(role).view_channel is True for role in leader_roles):
            return True
    return False


async def configure_join_access(member: discord.Member) -> None:
    community = configured_role(member.guild, "role.community")
    if community is None:
        raise RuntimeError("cargo role.community não configurado ou ID inválido; confira /install")
    issue = role_assignment_issue(member.guild, community)
    if issue:
        raise RuntimeError(f"não é possível atribuir o cargo community: {issue}")
    if community and community not in member.roles:
        await member.add_roles(community, reason="Entrada no servidor: cargo de comunidade")
    for key in JOIN_CHANNEL_KEYS:
        channel = configured_channel(member.guild, key)
        if channel is None:
            continue
        overwrite = channel.overwrites_for(community)
        overwrite.view_channel = True
        overwrite.send_messages = True
        try:
            await channel.set_permissions(
                community, overwrite=overwrite, reason="Acesso de boas-vindas da comunidade",
            )
        except discord.Forbidden:
            log.warning(
                "cargo community aplicado a %s, mas o Discord recusou a permissão no canal %s (%s); "
                "confira Gerenciar Cargos/permissões de canal",
                member.id, channel.name, channel.id,
            )


async def configure_operator_access(guild: discord.Guild, member: discord.Member) -> None:
    # Este é o cargo já configurado como membro aprovado; ele representa o
    # operador no fluxo, sem exigir um novo cargo ou uma nova chave de instalação.
    operator = configured_role(guild, "role.approved_member")
    if operator is None:
        raise RuntimeError("Configure o cargo existente de membro aprovado em /install.")
    leader_roles = _leadership_roles(guild)
    if not leader_roles:
        raise RuntimeError("Configure os cargos existentes de líder global e/ou líder de pelotão em /install.")

    apply_channel = configured_channel(guild, "channel.apply")
    candidates_channel = configured_channel(guild, "channel.candidates")
    excluded_ids = {getattr(apply_channel, "id", None), getattr(candidates_channel, "id", None)}
    leadership_channels = []

    # Reaproveita as salas existentes e suas permissões atuais. Não cria nem
    # remove canais: apenas concede o cargo já configurado nas salas comuns.
    for channel in guild.channels:
        if not _is_chat(channel):
            continue
        if channel.id in excluded_ids:
            continue
        if _is_leadership_only(channel, leader_roles):
            leadership_channels.append(channel)
            continue
        overwrite = channel.overwrites_for(operator)
        overwrite.view_channel = True
        if isinstance(channel, (discord.TextChannel, discord.ForumChannel)):
            overwrite.send_messages = True
            if isinstance(channel, discord.ForumChannel):
                overwrite.create_public_threads = True
                overwrite.send_messages_in_threads = True
        elif isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
            overwrite.connect = True
            overwrite.speak = True
            if isinstance(channel, discord.StageChannel):
                overwrite.request_to_speak = True
        await channel.set_permissions(operator, overwrite=overwrite, reason="Acesso do cargo de operador")

    # Community também vê apply. A exceção individual mantém o cargo, mas
    # impede que operadores acessem apply e as salas privadas dos líderes.
    excluded_for_member = list(leadership_channels)
    if apply_channel is not None:
        excluded_for_member.append(apply_channel)
    for channel in excluded_for_member:
        overwrite = channel.overwrites_for(member)
        overwrite.view_channel = False
        overwrite.send_messages = False
        await channel.set_permissions(
            member, overwrite=overwrite,
            reason="Operadores não acessam apply nem salas privadas de líderes",
        )
