from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
import re

import discord
from discord import ui

from ..content import MEMBER_RANKS, PLATOONS
from ..database import ApplicationDatabase, database
from ..models import MemberRecord
from .server_config import configured_role

RANK_LABELS = {
    "candidate": "Candidato",
    "operator": "Operador",
    "squad leader": "Líder de pelotão",
    "global leader": "Líder global",
}


def parse_birthday(value: str) -> str | None:
    """Return birthdays as MM-DD while accepting a DD/MM entry."""
    match = re.search(r"(?<!\d)(\d{1,2})\s*[/.-]\s*(\d{1,2})(?!\d)", value)
    if not match:
        return None
    day, month = map(int, match.groups())
    try:
        date(2000, month, day)
    except ValueError:
        return None
    return f"{month:02d}-{day:02d}"


def display_birthday(value: str | None) -> str:
    if not value:
        return "não informado"
    month, day = value.split("-", 1)
    return f"{day}/{month}"


def rank_label(rank: str) -> str:
    return RANK_LABELS.get(rank, rank.title())


@dataclass(frozen=True, slots=True)
class MemberScope:
    global_access: bool
    platoon: str | None


def actor_scope(interaction: discord.Interaction) -> MemberScope | None:
    roles = getattr(interaction.user, "roles", ())
    role_ids = {role.id for role in roles}
    global_role = configured_role(interaction.guild, "role.global_leader")
    squad_role = configured_role(interaction.guild, "role.squad_leader")
    if global_role and global_role.id in role_ids:
        return MemberScope(global_access=True, platoon=None)
    if squad_role is None or squad_role.id not in role_ids:
        return None
    actor = database.get_member(interaction.guild_id, interaction.user.id)
    if actor is None or actor.rank != "squad leader" or not actor.platoon:
        return None
    platoon_role = configured_role(interaction.guild, f"role.platoon.{actor.platoon.casefold()}")
    if platoon_role is None or platoon_role.id not in role_ids:
        return None
    return MemberScope(global_access=False, platoon=actor.platoon.casefold())


def can_manage(scope: MemberScope, target: MemberRecord) -> bool:
    return scope.global_access or (target.platoon is not None and target.platoon.casefold() == scope.platoon)


def roster_embed(guild: discord.Guild, scope: MemberScope,
                 repository: ApplicationDatabase = database) -> discord.Embed:
    members = repository.list_members(guild.id)
    if not scope.global_access:
        members = [member for member in members if can_manage(scope, member)]
    embed = discord.Embed(
        title="Gerenciamento de membros",
        description=("Cadastro interno salvo em SQLite. As ações deste menu não expulsam membros "
                    "nem alteram cargos do Discord. " +
                    ("Acesso global." if scope.global_access else f"Escopo: pelotão {scope.platoon.title()}.")),
        color=discord.Color.blurple(),
    )
    counts = Counter(member.platoon or "Sem pelotão" for member in members)
    platoons = " · ".join(f"{name.title()}: {count}" for name, count in sorted(counts.items())) or "Nenhum membro cadastrado"
    embed.add_field(name=f"Membros cadastrados ({len(members)})", value=platoons, inline=False)
    if members:
        lines = [
            f"<@{member.user_id}> · {rank_label(member.rank)} · "
            f"{member.platoon.title() if member.platoon else 'Sem pelotão'} · 🎂 {display_birthday(member.birthday)}"
            for member in members[:12]
        ]
        if len(members) > 12:
            lines.append(f"… e mais {len(members) - 12} membro(s)")
        embed.add_field(name="Cadastro", value="\n".join(lines), inline=False)
    else:
        embed.add_field(name="Cadastro", value="Ainda não há membros cadastrados.", inline=False)
    embed.set_footer(text="A data de aniversário fica visível apenas nos fluxos privados da staff.")
    return embed


class MemberManagementView(ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=300)
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id or actor_scope(interaction) is None:
            await interaction.response.send_message("Este menu é privado para quem o abriu e exige cargo e escopo de liderança válidos.", ephemeral=True)
            return False
        return True

    async def _pick(self, interaction: discord.Interaction, action: str):
        prompts = {
            "add": "Escolha o membro do servidor que deseja cadastrar.",
            "remove": "Escolha o cadastro que deseja remover.",
            "promote": "Escolha o membro que deseja promover.",
            "move": "Escolha o membro que deseja mover de pelotão.",
        }
        await interaction.response.send_message(
            prompts[action], ephemeral=True,
            view=MemberPickerView(self.owner_id, action),
        )

    @ui.button(label="Adicionar membro", emoji="➕", style=discord.ButtonStyle.success, row=0)
    async def add(self, interaction: discord.Interaction, button: ui.Button):
        await self._pick(interaction, "add")

    @ui.button(label="Remover membro", emoji="➖", style=discord.ButtonStyle.danger, row=0)
    async def remove(self, interaction: discord.Interaction, button: ui.Button):
        await self._pick(interaction, "remove")

    @ui.button(label="Promover membro", emoji="⬆️", style=discord.ButtonStyle.primary, row=1)
    async def promote(self, interaction: discord.Interaction, button: ui.Button):
        await self._pick(interaction, "promote")

    @ui.button(label="Mover de pelotão", emoji="🔀", style=discord.ButtonStyle.secondary, row=1)
    async def move(self, interaction: discord.Interaction, button: ui.Button):
        await self._pick(interaction, "move")


class MemberPickerView(ui.View):
    def __init__(self, owner_id: int, action: str):
        super().__init__(timeout=120)
        self.owner_id = owner_id
        self.action = action

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id or actor_scope(interaction) is None:
            await interaction.response.send_message("Este seletor pertence a outra interação ou seu escopo de liderança não é válido.", ephemeral=True)
            return False
        return True

    @ui.select(cls=ui.UserSelect, placeholder="Selecione um membro do servidor", min_values=1, max_values=1)
    async def member_select(self, interaction: discord.Interaction, select: ui.UserSelect):
        member: discord.Member = select.values[0]
        scope = actor_scope(interaction)
        if scope is None:
            return await interaction.response.send_message("Seu escopo de liderança não é válido.", ephemeral=True)
        if member.bot and self.action == "add":
            return await interaction.response.send_message("Contas de bot não podem ser adicionadas ao cadastro de membros.", ephemeral=True)
        if member.id == interaction.user.id and self.action != "add":
            return await interaction.response.send_message("Você não pode remover, promover ou mover o próprio cadastro por este menu.", ephemeral=True)
        record = database.get_member(interaction.guild_id, member.id)
        if self.action == "add":
            if record:
                return await interaction.response.send_message(f"{member.mention} já está no cadastro.", ephemeral=True)
            return await interaction.response.send_modal(AddMemberModal(
                member, initial_platoon=scope.platoon, actor_id=interaction.user.id,
            ))
        if record is None:
            return await interaction.response.send_message(f"{member.mention} ainda não está no cadastro SQLite.", ephemeral=True)
        if not can_manage(scope, record):
            return await interaction.response.send_message("Você só pode administrar membros cadastrados no seu próprio pelotão.", ephemeral=True)
        if self.action == "remove":
            embed = discord.Embed(title="Confirmar remoção do cadastro",
                description=f"Remover {member.mention} do cadastro interno? A conta não será expulsa do servidor.",
                color=discord.Color.red())
            return await interaction.response.send_message(embed=embed,
                view=MemberConfirmationView(self.owner_id, "remove", member.id), ephemeral=True)
        if self.action == "promote":
            try:
                next_rank_index = MEMBER_RANKS.index(record.rank) + 1
                if not scope.global_access and next_rank_index >= MEMBER_RANKS.index("global leader"):
                    next_rank_index = len(MEMBER_RANKS)
                next_rank = MEMBER_RANKS[next_rank_index]
            except (ValueError, IndexError):
                return await interaction.response.send_message(f"{member.mention} já está no nível máximo ({rank_label(record.rank)}).", ephemeral=True)
            embed = discord.Embed(title="Confirmar promoção",
                description=f"Promover {member.mention}: **{rank_label(record.rank)} → {rank_label(next_rank)}**?\n\nA mudança será registrada no cadastro SQLite.",
                color=discord.Color.gold())
            return await interaction.response.send_message(embed=embed,
                view=MemberConfirmationView(self.owner_id, "promote", member.id), ephemeral=True)
        if self.action == "move":
            platoons = _platoon_names(interaction.guild)
            return await interaction.response.send_message(
                f"Pelotão atual de {member.mention}: **{record.platoon.title() if record.platoon else 'nenhum'}**. Escolha o destino.",
                view=PlatoonSelectView(self.owner_id, member.id, platoons), ephemeral=True)


class AddMemberModal(ui.Modal, title="Adicionar membro ao cadastro"):
    birthday = ui.TextInput(label="Aniversário (DD/MM)", placeholder="Ex.: 17/04", required=False, max_length=5)

    def __init__(self, member: discord.Member, *, initial_platoon: str | None, actor_id: int):
        super().__init__(timeout=120)
        self.member_id = member.id
        self.username = member.name
        self.display_name = member.display_name
        self.initial_platoon = initial_platoon
        self.actor_id = actor_id

    async def on_submit(self, interaction: discord.Interaction):
        scope = actor_scope(interaction)
        if interaction.user.id != self.actor_id or scope is None:
            return await interaction.response.send_message("Seu acesso ao cadastro foi revogado ou expirou.", ephemeral=True)
        if not scope.global_access and scope.platoon != self.initial_platoon:
            return await interaction.response.send_message("Seu pelotão mudou; abra o menu novamente.", ephemeral=True)
        raw = self.birthday.value.strip()
        normalized = parse_birthday(raw) if raw else None
        if raw and not normalized:
            return await interaction.response.send_message("Data inválida. Informe o aniversário no formato DD/MM, por exemplo 17/04.", ephemeral=True)
        added = database.add_member(guild_id=interaction.guild_id, user_id=self.member_id,
            username=self.username, display_name=self.display_name, birthday=normalized)
        if added and self.initial_platoon:
            database.set_platoon(interaction.guild_id, self.member_id, self.initial_platoon)
        message = "✅ Membro adicionado ao cadastro SQLite." if added else "ℹ️ Esse membro já está cadastrado."
        await interaction.response.send_message(message, ephemeral=True)


class MemberConfirmationView(ui.View):
    def __init__(self, owner_id: int, action: str, member_id: int):
        super().__init__(timeout=60)
        self.owner_id = owner_id
        self.action = action
        self.member_id = member_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        scope = actor_scope(interaction)
        target = database.get_member(interaction.guild_id, self.member_id)
        allowed = (interaction.user.id == self.owner_id and scope is not None and
                   (target is None or can_manage(scope, target)))
        if not allowed:
            await interaction.response.send_message("Este menu exige liderança válida e o membro deve estar no seu escopo.", ephemeral=True)
        return allowed

    @ui.button(label="Confirmar", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        if self.action == "remove":
            success = database.remove_member(interaction.guild_id, self.member_id)
            result = "✅ Cadastro removido." if success else "ℹ️ O cadastro já não existe."
        else:
            updated = database.promote_member(interaction.guild_id, self.member_id)
            result = f"✅ Promoção registrada: **{rank_label(updated.rank)}**." if updated else "Cadastro não encontrado."
        await interaction.response.edit_message(content=result, embed=None, view=None)

    @ui.button(label="Cancelar", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content="Ação cancelada.", embed=None, view=None)


class PlatoonSelectView(ui.View):
    def __init__(self, owner_id: int, member_id: int, platoons: list[str]):
        super().__init__(timeout=120)
        self.owner_id = owner_id
        self.member_id = member_id
        options = [discord.SelectOption(label=f"Pelotão {name.title()}", value=name) for name in platoons[:24]]
        options.append(discord.SelectOption(label="Sem pelotão", value="__none__"))
        self.add_item(PlatoonSelect(options))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        scope = actor_scope(interaction)
        target = database.get_member(interaction.guild_id, self.member_id)
        allowed = interaction.user.id == self.owner_id and scope is not None and target is not None and can_manage(scope, target)
        if not allowed:
            await interaction.response.send_message("O membro não está mais no seu escopo de administração.", ephemeral=True)
        return allowed


class PlatoonSelect(ui.Select):
    def __init__(self, options: list[discord.SelectOption]):
        super().__init__(placeholder="Selecione o pelotão de destino", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        view: PlatoonSelectView = self.view
        value = self.values[0]
        platoon = None if value == "__none__" else value
        updated = database.set_platoon(interaction.guild_id, view.member_id, platoon)
        if updated is None:
            result = "Cadastro não encontrado."
        else:
            label = f"Pelotão {platoon.title()}" if platoon else "sem pelotão"
            result = f"✅ Movimentação registrada: <@{view.member_id}> agora está em **{label}**."
        await interaction.response.edit_message(content=result, view=None)


def _platoon_names(guild: discord.Guild) -> list[str]:
    return [name for name in PLATOONS
            if configured_role(guild, f"role.platoon.{name}") is not None]
