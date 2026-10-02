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
from .server_config import configured_channel, configured_role, configured_roles, role_assignment_issue
from .presentation import card, result

log = get_logger(__name__)


def load_config(filename: str):
    return load_json(filename, {}) or {}


def welcome_config():
    return WELCOME


def application_config():
    return APPLICATION


class WelcomeView(ui.View):
    def __init__(self, guild: discord.Guild, *, picker: bool = True, platform_key: str | None = None, member=None):
        super().__init__(timeout=None)
        cfg = welcome_config()
        platform = cfg.get("platforms", {}).get(platform_key, {})
        if picker:
            self.embed = card(cfg.get("title", "Boas-vindas à DEFCOM"), cfg.get("intro", ""), tone="brand")
            self.embed.add_field(name="Escolha sua plataforma", value=cfg.get("platformQuestion", "Qual é a sua plataforma?"), inline=False)
            for key, option in cfg.get("platforms", {}).items():
                self.add_item(ui.Button(label=option["label"], style=discord.ButtonStyle.primary,
                                        custom_id=f"welcome:platform:{key}"))
            self.embed.set_footer(text=cfg.get("footer", "DEFCOM • Boas-vindas"))
        else:
            name = getattr(member, "display_name", "")
            body = str(platform.get("message", "")).replace("{name}", name)
            recs = "\n".join(
                f"• {configured_channel(guild, f'channel.{target}').mention if configured_channel(guild, f'channel.{target}') else 'Canal não configurado'}"
                for target in platform.get("recommend", [])
            )
            icon = guild.icon.url if guild.icon else None
            self.embed = card(platform.get("headline", "Bem-vindo"), body, tone="brand")
            if icon:
                self.embed.set_thumbnail(url=icon)
            self.embed.add_field(name="Canais recomendados", value=recs or "Nenhum canal recomendado foi configurado.", inline=False)
            apply = configured_channel(guild, "channel.apply")
            if apply:
                self.add_item(ui.Button(label="Abrir candidatura", style=discord.ButtonStyle.link, url=apply.jump_url))
            self.add_item(ui.Button(label="Trocar plataforma", style=discord.ButtonStyle.secondary, custom_id="welcome:back"))
            self.embed.set_footer(text=cfg.get("footer", "DEFCOM • Boas-vindas"))


class ApplyPageView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        cfg = application_config()
        self.embed = card(cfg.get("title", "Candidatura DEFCOM"), cfg.get("intro", ""), tone="brand")
        steps = "\n".join(f"{i}. {step}" for i, step in enumerate(cfg.get("steps", []), 1))
        requirements = "\n".join(f"• {item}" for item in cfg.get("requirements", []))
        self.embed.add_field(name="Como funciona", value=steps or "As etapas serão informadas pela staff.", inline=False)
        self.embed.add_field(name="Requisitos", value=requirements or "Consulte a staff.", inline=False)
        self.embed.set_footer(text="Leia os termos antes de iniciar; o formulário pedirá a confirmação.")
        self.add_item(ui.Button(label="Ler os termos", style=discord.ButtonStyle.secondary, custom_id="apply:terms"))
        self.add_item(ui.Button(label="Iniciar candidatura", style=discord.ButtonStyle.success, custom_id="apply:start"))


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
    tone = "success" if decision == "approve" else "error" if decision == "deny" else "brand"
    embed = card(
        "Candidatura recebida" if decision is None else "Candidatura aprovada" if decision == "approve" else "Candidatura não aprovada",
        f"**Candidato:** <@{applicant.id}> (`{getattr(applicant, 'name', 'candidato')}`)",
        tone=tone,
    )
    for field in cfg.get("fields", []):
        embed.add_field(name=field["label"], value=answers.get(field["id"]) or "Não informado", inline=False)
    view = ui.View(timeout=None)
    if decision:
        embed.add_field(name="Decisão", value=f"**Avaliada por:** {reviewer}", inline=False)
        if note:
            embed.add_field(name="Resultado operacional", value=note, inline=False)
    else:
        view.add_item(ui.Button(label="Aprovar candidatura", style=discord.ButtonStyle.success, custom_id=f"review:approve:{applicant.id}"))
        view.add_item(ui.Button(label="Reprovar candidatura", style=discord.ButtonStyle.danger, custom_id=f"review:deny:{applicant.id}"))
    return embed, view


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
            embed=card("Confirmação dos termos", "Para enviar a candidatura, digite **CONCORDO** no campo de confirmação dos termos.", tone="warning"),
            ephemeral=True,
        )
        return
    age_and_birthday = answers.get("age_birthday", "")
    birthday = parse_birthday(age_and_birthday)
    before_date = re.split(r"\b\d{1,2}\s*[/.-]\s*\d{1,2}\b", age_and_birthday, maxsplit=1)[0]
    age = re.search(r"\b(\d{1,3})\b", before_date)
    if not birthday or not age:
        await interaction.response.send_message(
            embed=card("Revise seus dados", "Informe idade e aniversário no formato indicado, por exemplo: `22 anos, aniversário em 17/04`.", tone="warning"),
            ephemeral=True,
        )
        return
    answers["birthday"] = birthday
    answers["age"] = age.group(1)
    if find_pending_application(interaction.guild_id, interaction.user.id):
        await interaction.response.send_message(embed=card("Candidatura em análise", "Sua candidatura já está com a staff. Aguarde o retorno antes de enviar outra.", tone="warning"), ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    candidate_role = configured_role(interaction.guild, "role.candidate")
    if candidate_role is None:
        return await interaction.followup.send(
            embed=card("Configuração incompleta", "O cargo de candidato não está configurado. Peça ao dono do servidor para revisar `/install`.", tone="error"),
            ephemeral=True,
        )
    assignment_issue = role_assignment_issue(interaction.guild, candidate_role)
    if assignment_issue:
        return await interaction.followup.send(
            embed=card("Cargo de candidato indisponível", f"Não consigo atribuir o cargo: {assignment_issue}. Avise a staff para corrigir a hierarquia ou as permissões do bot.", tone="error"),
            ephemeral=True,
        )
    channel = await ensure_staff_channel(interaction.guild)
    application_embed, application_controls = application_view(cfg, interaction.user, answers)
    try:
        application_id = database.create_application(
            guild_id=interaction.guild_id, user_id=interaction.user.id,
            username=interaction.user.name, answers=answers,
        )
    except sqlite3.IntegrityError:
        return await interaction.followup.send(
            embed=card("Candidatura em análise", "Sua candidatura já está com a staff. Aguarde o retorno antes de enviar outra.", tone="warning"),
            ephemeral=True,
        )
    try:
        message = await channel.send(embed=application_embed, view=application_controls)
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
            embed=card("Não foi possível enviar", "O Discord recusou a atribuição do cargo de candidato, então a candidatura não foi registrada. Avise a staff para conferir as permissões e a hierarquia de cargos.", tone="error"),
            ephemeral=True,
        )
    await interaction.followup.send(embed=result("Candidatura enviada", "A staff vai avaliar suas respostas e retornar assim que possível."), ephemeral=True)


async def route_button(interaction: discord.Interaction):
    custom_id = interaction.data.get("custom_id", "")
    parts = custom_id.split(":")
    if parts[:2] == ["welcome", "platform"]:
        cfg = welcome_config()
        key = parts[2] if len(parts) > 2 else ""
        if key not in cfg.get("platforms", {}):
            return await interaction.response.send_message(embed=card("Opção indisponível", "Não reconheci essa plataforma. Abra novamente a mensagem de boas-vindas.", tone="error"), ephemeral=True)
        role = configured_role(interaction.guild, "role.community")
        if role and role not in interaction.user.roles:
            try:
                await interaction.user.add_roles(role)
            except discord.HTTPException as error:
                log.warning("não foi possível atribuir community: %s", error)
        welcome = WelcomeView(interaction.guild, picker=False, platform_key=key, member=interaction.user)
        return await interaction.response.send_message(embed=welcome.embed, view=welcome, ephemeral=True)
    if custom_id == "welcome:back":
        welcome = WelcomeView(interaction.guild)
        return await interaction.response.edit_message(embed=welcome.embed, view=welcome)
    if custom_id == "apply:start":
        if find_pending_application(interaction.guild_id, interaction.user.id):
            return await interaction.response.send_message(embed=card("Candidatura em análise", "A staff ainda está avaliando sua candidatura. Aguarde o retorno antes de enviar outra.", tone="warning"), ephemeral=True)
        return await interaction.response.send_modal(ApplicationModal(application_config()))
    if custom_id == "apply:terms":
        cfg = application_config()
        terms = "\n".join(f"{index}. {term}" for index, term in enumerate(cfg.get("terms", []), start=1))
        embed = card("Termos da candidatura", terms or "Os termos ainda não foram configurados.", tone="brand",
                     footer="Para confirmar, digite CONCORDO no formulário de candidatura.")
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    if parts[0] == "review":
        return await handle_review(interaction, parts[1], int(parts[2]))


async def handle_review(interaction: discord.Interaction, decision: str, user_id: int):
    cfg = application_config()
    staff_role_ids = {role.id for role in configured_roles(interaction.guild, "staff_roles")}
    if (interaction.user.id != interaction.guild.owner_id
            and not any(role.id in staff_role_ids for role in getattr(interaction.user, "roles", ()))):
        return await interaction.response.send_message(embed=card("Acesso restrito", "Apenas a staff pode avaliar candidaturas.", tone="error"), ephemeral=True)
    record = _application_record(interaction.message.id)
    if record is None or record.status != "pending" or record.user_id != str(user_id):
        return await interaction.response.send_message(embed=card("Candidatura indisponível", "Esta candidatura não existe ou já foi decidida.", tone="warning"), ephemeral=True)
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
                    await applicant.send(embed=result("Candidatura aprovada", "Sua candidatura na DEFCOM foi aprovada. Seja bem-vindo(a) à equipe."))
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
                    embed=card("Aprovação incompleta", f"Não foi possível concluir a aprovação e configurar os acessos.\n\nDetalhe: {error}", tone="error"), ephemeral=True,
                )
            except RuntimeError as error:
                return await interaction.followup.send(embed=card("Aprovação incompleta", str(error), tone="error"), ephemeral=True)
        else:
            return await interaction.followup.send(
                embed=card("Configuração incompleta", "O cargo existente de membro aprovado não está configurado. Peça ao dono do servidor para revisar `/install`.", tone="error"), ephemeral=True,
            )
    elif decision == "deny" and applicant:
        candidate_role = configured_role(interaction.guild, "role.candidate")
        if candidate_role and candidate_role in applicant.roles:
            try:
                await applicant.remove_roles(candidate_role, reason="Candidatura não aprovada")
            except discord.HTTPException as error:
                return await interaction.followup.send(
                    embed=card("Falha ao atualizar cargos", f"Não foi possível remover o cargo de candidato.\n\nDetalhe: {error}", tone="error"), ephemeral=True,
                )
        try:
            await applicant.send(embed=card(
                "Retorno sobre sua candidatura",
                "Obrigado por dedicar seu tempo ao processo da DEFCOM. Desta vez, a candidatura não foi aprovada, "
                "mas isso não define seu potencial. Continue evoluindo e fique à vontade para tentar novamente "
                "quando estiver pronto. Seu cargo de comunidade foi mantido.",
                tone="warning",
            ))
        except discord.HTTPException:
            pass
    user_proxy = type("Applicant", (), {"id": user_id, "name": record.username})()
    reviewed_embed, reviewed_view = application_view(cfg, user_proxy, record.answers, decision, interaction.user, note)
    await interaction.message.edit(embed=reviewed_embed, view=reviewed_view)
    database.decide_application(
        message_id=interaction.message.id, decision=decision,
        reviewer_id=interaction.user.id,
    )
    await interaction.followup.send(embed=result("Avaliação registrada", "A decisão foi salva no cadastro de candidaturas."), ephemeral=True)


async def publish_pages(guild: discord.Guild, *, welcome: bool = True, apply: bool = True):
    store = load_config("published.json")
    if welcome:
        channel = configured_channel(guild, "channel.welcome")
        if not channel:
            raise ValueError("Canal de boas-vindas não configurado. Execute /install.")
        view = WelcomeView(guild)
        await _replace_published(channel, "welcome", view.embed, view, store)
    if apply:
        await ensure_staff_channel(guild)
        channel = configured_channel(guild, "channel.apply")
        if not channel:
            raise ValueError("Canal da página de candidatura não configurado. Execute /install.")
        view = ApplyPageView()
        await _replace_published(channel, "apply", view.embed, view, store)
    from ..storage import save_json
    save_json("published.json", store)


async def _replace_published(channel, key: str, embed: discord.Embed, view: ui.View, store: dict):
    previous = store.get(key, {})
    if previous.get("messageId"):
        try:
            old = await channel.fetch_message(int(previous["messageId"]))
            await old.delete()
        except discord.HTTPException:
            pass
    message = await channel.send(embed=embed, view=view)
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
