from __future__ import annotations

import sqlite3
import re
import discord
from discord import app_commands, ui

from ..content import APPLICATION, WELCOME
from ..database import database
from ..log import get_logger
from ..storage import load_json
from .member_management import parse_birthday
from .member_access import configure_operator_access
from .server_config import configured_channel, configured_role, configured_roles
from .ui import hex_to_int, separator, text

log = get_logger(__name__)


def load_config(filename: str):
    return load_json(filename, {}) or {}


def welcome_config():
    return WELCOME


def application_config():
    return APPLICATION


def _layout(*items, accent: int | None = None) -> ui.LayoutView:
    view = ui.LayoutView(timeout=None)
    view.add_item(ui.Container(*items, accent_color=accent))
    return view


class WelcomeView(ui.LayoutView):
    def __init__(self, guild: discord.Guild, *, picker: bool = True, platform_key: str | None = None, member=None):
        super().__init__(timeout=None)
        cfg = welcome_config()
        accent = hex_to_int(cfg.get("accentColor"))
        platform = cfg.get("platforms", {}).get(platform_key, {})
        if picker:
            heading = f"**{cfg.get('platformQuestion', 'Qual sua plataforma?')}**"
            children = [text(f"# {cfg.get('title', '')}\n{cfg.get('intro', '')}"), separator(), text(heading)]
            row = ui.ActionRow()
            for key, option in cfg.get("platforms", {}).items():
                row.add_item(ui.Button(label=option["label"], emoji=option.get("emoji"), style=discord.ButtonStyle.primary,
                                       custom_id=f"welcome:platform:{key}"))
            children.append(row)
            children.extend([separator(False), text(cfg.get("footer", ""))])
        else:
            name = getattr(member, "display_name", "")
            body = str(platform.get("message", "")).replace("{name}", name)
            recs = "\n".join(
                f"• {configured_channel(guild, f'channel.{target}').mention if configured_channel(guild, f'channel.{target}') else 'Canal não configurado'}"
                for target in platform.get("recommend", [])
            )
            icon = guild.icon.url if guild.icon else None
            header = ui.Section(text(f"# {platform.get('headline', '')}\n{body}"), accessory=ui.Thumbnail(icon)) if icon else text(f"# {platform.get('headline', '')}\n{body}")
            row = ui.ActionRow()
            apply = configured_channel(guild, "channel.apply")
            if apply:
                row.add_item(ui.Button(label="Ir para #apply", emoji="📝", style=discord.ButtonStyle.link, url=apply.jump_url))
            row.add_item(ui.Button(label="Trocar plataforma", emoji="🔁", style=discord.ButtonStyle.secondary, custom_id="welcome:back"))
            children = [header, separator(), text(f"**Salas recomendadas**\n{recs}"), separator(), row]
        self.add_item(ui.Container(*children, accent_color=accent))


class ApplyPageView(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        cfg = application_config()
        row = ui.ActionRow(
            ui.Button(label="Ler os termos", style=discord.ButtonStyle.secondary, custom_id="apply:terms"),
            ui.Button(label="Iniciar candidatura", style=discord.ButtonStyle.success, custom_id="apply:start"),
        )
        steps = "\n".join(f"{i}. {step}" for i, step in enumerate(cfg.get("steps", []), 1))
        requirements = "\n".join(f"• {item}" for item in cfg.get("requirements", []))
        children = [
            text(f"# {cfg.get('title', '')}\n\n{cfg.get('intro', '')}"),
            separator(),
            text(f"## Como funciona\n\n{steps}"),
            separator(),
            text(f"## Requisitos\n\n{requirements}"),
            separator(visible=False),
            text("Leia os termos antes de iniciar. A confirmação de concordância será solicitada no formulário."),
            row,
        ]
        self.add_item(ui.Container(*children, accent_color=hex_to_int(cfg.get("accentColor"))))


class ApplicationModal(ui.Modal):
    def __init__(self, cfg: dict):
        super().__init__(title=cfg.get("modalTitle", "Candidatura DEFCOM")[:45], custom_id="apply:modal", timeout=None)
        self.fields_cfg = cfg.get("fields", [])
        for field in self.fields_cfg:
            if len(self.children) >= 5:
                break
            self.add_item(ui.TextInput(label=field["label"][:45], custom_id=field["id"],
                style=discord.TextStyle.paragraph if field.get("style") == "paragraph" else discord.TextStyle.short,
                required=field.get("required", True), max_length=500 if field.get("style") == "paragraph" else 100,
                placeholder=field.get("placeholder", "")[:100] or None))

    async def on_submit(self, interaction: discord.Interaction):
        await submit_application(interaction, self.fields_cfg, {item.custom_id: item.value for item in self.children})


def _application_record(message_id: int):
    return database.get_application_by_message(message_id)


def find_pending_application(guild_id: int, user_id: int) -> bool:
    return database.has_pending_application(guild_id, user_id)


def application_view(cfg: dict, applicant, answers: dict, decision: str | None = None, reviewer=None, note: str = ""):
    accent = 0x3AD98E if decision == "approve" else 0xE74C3C if decision == "deny" else hex_to_int(cfg.get("accentColor"))
    fields = "\n".join(f"**{field['label']}:** {answers.get(field['id']) or 'não informado'}" for field in cfg.get("fields", []))
    children = [
        text(f"# Respostas da candidatura\n\n**Candidato:** <@{applicant.id}> (`{getattr(applicant, 'name', 'candidato')}`)"),
        separator(),
        text(f"## Respostas\n\n{fields}"),
        separator(),
    ]
    if decision:
        label = "Aprovada" if decision == "approve" else "Reprovada"
        children.append(text(f"**Decisão:** {label}\n**Avaliada por:** {reviewer}"))
        if note:
            children.append(text(note))
    else:
        row = ui.ActionRow(
            ui.Button(label="Aprovar", style=discord.ButtonStyle.success, custom_id=f"review:approve:{applicant.id}"),
            ui.Button(label="Reprovar", style=discord.ButtonStyle.danger, custom_id=f"review:deny:{applicant.id}"))
        children.extend([text("-# Avaliação da staff"), row])
    return _layout(*children, accent=accent)


async def ensure_staff_channel(guild: discord.Guild):
    channel = configured_channel(guild, "channel.candidates")
    if channel is None:
        configured_id = database.get_guild_config(guild.id, "channel.candidates")
        if configured_id is not None:
            raise RuntimeError("O ID salvo para o canal de candidaturas não existe mais. Corrija em /install.")
        raise RuntimeError("Configure no `/install` o canal de candidaturas existente antes de receber applies.")
    me = guild.me
    if channel:
        permissions = channel.permissions_for(me)
        if permissions.view_channel and permissions.send_messages:
            return channel
        try:
            await channel.set_permissions(me, view_channel=True, send_messages=True)
            return channel
        except discord.HTTPException as error:
            raise RuntimeError(f"O canal #{channel.name} existe mas o bot não tem acesso. Detalhe: {error}") from error
    raise RuntimeError(f"O bot não tem acesso ao canal {channel.mention} configurado para candidaturas.")


async def submit_application(interaction: discord.Interaction, fields_cfg: list[dict], answers: dict[str, str]):
    cfg = application_config()
    if answers.get("agreement", "").strip().casefold() != "concordo":
        await interaction.response.send_message(
            "Para enviar a candidatura, digite **CONCORDO** no campo de confirmação dos termos.",
            ephemeral=True,
        )
        return
    age_and_birthday = answers.get("age_birthday", "")
    birthday = parse_birthday(age_and_birthday)
    before_date = re.split(r"\b\d{1,2}\s*[/.-]\s*\d{1,2}\b", age_and_birthday, maxsplit=1)[0]
    age = re.search(r"\b(\d{1,3})\b", before_date)
    if not birthday or not age:
        await interaction.response.send_message(
            "Informe idade e aniversário no formato indicado (ex.: 22 anos, aniversário em 17/04).",
            ephemeral=True,
        )
        return
    answers["birthday"] = birthday
    answers["age"] = age.group(1)
    if find_pending_application(interaction.guild_id, interaction.user.id):
        await interaction.response.send_message("⏳ Você já tem uma candidatura **em análise** pela staff. Aguarde o retorno.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    candidate_role = configured_role(interaction.guild, "role.candidate")
    if candidate_role is None:
        return await interaction.followup.send(
            "O cargo de candidato não está configurado. Peça ao dono do servidor para revisar `/install`.",
            ephemeral=True,
        )
    channel = await ensure_staff_channel(interaction.guild)
    layout = application_view(cfg, interaction.user, answers)
    try:
        application_id = database.create_application(
            guild_id=interaction.guild_id, user_id=interaction.user.id,
            username=interaction.user.name, answers=answers,
        )
    except sqlite3.IntegrityError:
        return await interaction.followup.send(
            "⏳ Você já tem uma candidatura **em análise** pela staff. Aguarde o retorno.",
            ephemeral=True,
        )
    try:
        message = await channel.send(view=layout)
        database.set_application_message(application_id, message.id)
    except Exception:
        database.delete_application(application_id)
        raise
    try:
        await interaction.user.add_roles(candidate_role, reason="Candidatura enviada")
    except discord.HTTPException as error:
        database.delete_application(application_id)
        try:
            await message.delete()
        except discord.HTTPException:
            pass
        log.warning("não foi possível atribuir o cargo de candidato: %s", error)
        return await interaction.followup.send(
            "Não consegui atribuir o cargo de candidato, então a candidatura não foi registrada. Avise a staff.",
            ephemeral=True,
        )
    await interaction.followup.send("✅ Candidatura enviada! A staff vai avaliar e te dar um retorno em breve.", ephemeral=True)


async def route_button(interaction: discord.Interaction):
    custom_id = interaction.data.get("custom_id", "")
    parts = custom_id.split(":")
    if parts[:2] == ["welcome", "platform"]:
        cfg = welcome_config()
        key = parts[2] if len(parts) > 2 else ""
        if key not in cfg.get("platforms", {}):
            return await interaction.response.send_message("Plataforma desconhecida.", ephemeral=True)
        role = configured_role(interaction.guild, "role.community")
        if role and role not in interaction.user.roles:
            try:
                await interaction.user.add_roles(role)
            except discord.HTTPException as error:
                log.warning("não foi possível atribuir community: %s", error)
        return await interaction.response.send_message(view=WelcomeView(interaction.guild, picker=False, platform_key=key, member=interaction.user), ephemeral=True)
    if custom_id == "welcome:back":
        return await interaction.response.edit_message(view=WelcomeView(interaction.guild))
    if custom_id == "apply:start":
        if find_pending_application(interaction.guild_id, interaction.user.id):
            return await interaction.response.send_message("⏳ Você já tem uma candidatura **em análise** pela staff. Aguarde o retorno antes de enviar outra.", ephemeral=True)
        return await interaction.response.send_modal(ApplicationModal(application_config()))
    if custom_id == "apply:terms":
        cfg = application_config()
        terms = "\n".join(f"{index}. {term}" for index, term in enumerate(cfg.get("terms", []), start=1))
        embed = discord.Embed(
            title="Termos da candidatura",
            description=terms or "Os termos ainda não foram configurados.",
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="Para confirmar, digite CONCORDO no formulário de candidatura.")
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    if parts[0] == "review":
        return await handle_review(interaction, parts[1], int(parts[2]))


async def handle_review(interaction: discord.Interaction, decision: str, user_id: int):
    cfg = application_config()
    staff_role_ids = {role.id for role in configured_roles(interaction.guild, "staff_roles")}
    if (interaction.user.id != interaction.guild.owner_id
            and not any(role.id in staff_role_ids for role in getattr(interaction.user, "roles", ()))):
        return await interaction.response.send_message("❌ Apenas a staff pode avaliar candidaturas.", ephemeral=True)
    record = _application_record(interaction.message.id)
    if record is None or record.status != "pending" or record.user_id != str(user_id):
        return await interaction.response.send_message("Esta candidatura não existe ou já foi decidida.", ephemeral=True)
    await interaction.response.defer(ephemeral=True, thinking=True)
    applicant = interaction.guild.get_member(user_id)
    if applicant is None:
        try:
            applicant = await interaction.guild.fetch_member(user_id)
        except discord.HTTPException as error:
            log.warning("candidato %s não encontrado: %s", user_id, error)
    note = ""
    if decision == "approve" and applicant:
        role = configured_role(interaction.guild, "role.approved_member")
        if role:
            try:
                await configure_operator_access(interaction.guild, applicant)
                await applicant.add_roles(role, reason="Candidatura aprovada: cargo de operador")
                candidate_role = configured_role(interaction.guild, "role.candidate")
                if candidate_role and candidate_role in applicant.roles:
                    await applicant.remove_roles(candidate_role, reason="Candidatura aprovada")
                note = f"Cargo `{role.name}` atribuído; cargo de candidato removido."
                try:
                    await applicant.send("✅ Sua candidatura na DEFCOM foi **aprovada**! Bem-vindo(a) ao time.")
                except discord.HTTPException:
                    pass
                database.upsert_approved_member(
                    guild_id=interaction.guild_id, user_id=applicant.id,
                    username=applicant.name, display_name=applicant.display_name,
                    birthday=record.answers.get("birthday"),
                )
            except discord.HTTPException as error:
                log.warning("falha ao completar aprovação de %s: %s", applicant.id, error)
                return await interaction.followup.send(
                    f"Não foi possível concluir a aprovação e configurar os acessos: {error}", ephemeral=True,
                )
            except RuntimeError as error:
                return await interaction.followup.send(str(error), ephemeral=True)
        else:
            return await interaction.followup.send(
                "Cargo existente de membro aprovado não configurado. Peça ao dono do servidor para revisar `/install`.", ephemeral=True,
            )
    elif decision == "deny" and applicant:
        candidate_role = configured_role(interaction.guild, "role.candidate")
        if candidate_role and candidate_role in applicant.roles:
            try:
                await applicant.remove_roles(candidate_role, reason="Candidatura não aprovada")
            except discord.HTTPException as error:
                return await interaction.followup.send(
                    f"Não foi possível remover o cargo de candidato: {error}", ephemeral=True,
                )
        try:
            await applicant.send(
                "Obrigado por dedicar seu tempo à candidatura da DEFCOM. Neste momento, ela não foi aprovada, "
                "mas isso não define seu potencial. Continue evoluindo e fique à vontade para tentar novamente "
                "quando estiver pronto. Seu cargo de comunidade foi mantido."
            )
        except discord.HTTPException:
            pass
    user_proxy = type("Applicant", (), {"id": user_id, "name": record.username})()
    await interaction.message.edit(view=application_view(cfg, user_proxy, record.answers, decision, interaction.user, note))
    database.decide_application(
        message_id=interaction.message.id, decision=decision,
        reviewer_id=interaction.user.id,
    )
    await interaction.followup.send("Candidatura avaliada.", ephemeral=True)


async def publish_pages(guild: discord.Guild, *, welcome: bool = True, apply: bool = True):
    store = load_config("published.json")
    if welcome:
        channel = configured_channel(guild, "channel.welcome")
        if not channel:
            raise ValueError("Canal de boas-vindas não configurado. Execute /install.")
        await _replace_published(channel, "welcome", WelcomeView(guild), store)
    if apply:
        await ensure_staff_channel(guild)
        channel = configured_channel(guild, "channel.apply")
        if not channel:
            raise ValueError("Canal da página de candidatura não configurado. Execute /install.")
        await _replace_published(channel, "apply", ApplyPageView(), store)
    from ..storage import save_json
    save_json("published.json", store)


async def _replace_published(channel, key: str, view: ui.LayoutView, store: dict):
    previous = store.get(key, {})
    if previous.get("messageId"):
        try:
            old = await channel.fetch_message(int(previous["messageId"]))
            await old.delete()
        except discord.HTTPException:
            pass
    message = await channel.send(view=view)
    try:
        await message.pin()
    except discord.HTTPException:
        pass
    store[key] = {"channelId": str(channel.id), "messageId": str(message.id)}


async def register_persistent_views(bot: discord.Client):
    bot.add_view(WelcomeViewPlaceholder())


class WelcomeViewPlaceholder(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for key in welcome_config().get("platforms", {}):
            self.add_item(ui.Button(label=key.upper(), custom_id=f"welcome:platform:{key}", style=discord.ButtonStyle.primary))
        self.add_item(ui.Button(label="Trocar plataforma", custom_id="welcome:back", style=discord.ButtonStyle.secondary))
        self.add_item(ui.Button(label="Iniciar candidatura", custom_id="apply:start", style=discord.ButtonStyle.success))
