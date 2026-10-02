from __future__ import annotations

import asyncio
import discord
import random
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, time as datetime_time
from zoneinfo import ZoneInfo

from .config import settings
from .content import BIRTHDAY_MESSAGES, PRESENCE_MESSAGES
from .database import database
from .log import get_logger
from .discord.commands import setup as setup_commands
from .discord.interactions import register_persistent_views, route_button
from .discord.map_service import map_guild
from .discord.server_config import configured_role
from .discord.server_config import configured_channel
from .discord.warning_editor import send_warning_editor
from .discord.member_access import configure_join_access

log = get_logger("defcom_bot")
BIRTHDAY_TIMEZONE = ZoneInfo("America/Sao_Paulo")


class DefcomBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.none()
        intents.guilds = True
        # Required for automatic community-role assignment on member_join.
        intents.members = True
        intents.messages = True
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self._startup_map_done = False
        self._presence_index = 0
        self._birthday_catchup_done = False
        self._birthday_lock = asyncio.Lock()

    async def setup_hook(self):
        database.initialize()
        await setup_commands(self)
        await register_persistent_views(self)
        guild = discord.Object(id=settings.guild_id)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        log.info("slash commands registrados (%d) na guild %s", len(synced), settings.guild_id)

    async def on_ready(self):
        log.info("conectado como %s", self.user)
        if not self.rotate_presence.is_running():
            self.rotate_presence.start()
        if not self.birthday_check.is_running():
            self.birthday_check.start()
        if not self._birthday_catchup_done:
            self._birthday_catchup_done = True
            try:
                await self.announce_birthdays()
            except Exception:
                log.exception("falha na verificação inicial de aniversários")
        if self._startup_map_done:
            return
        self._startup_map_done = True
        try:
            guild = self.get_guild(settings.guild_id)
            if guild is None:
                log.warning("guild %s ainda não está no cache; snapshot automático ignorado", settings.guild_id)
                return
            snapshot, json_path, md_path = await map_guild(guild)
            log.info(
                "snapshot inicial atualizado para %s: %d canais, %d cargos (%s, %s)",
                guild.name,
                sum(len(category["channels"]) for category in snapshot["categories"])
                + len(snapshot["uncategorized"]),
                len(snapshot["roles"]), json_path, md_path,
            )
        except Exception:
            log.exception("falha ao atualizar o snapshot inicial")

    @tasks.loop(seconds=30)
    async def rotate_presence(self):
        message = PRESENCE_MESSAGES[self._presence_index]
        self._presence_index = (self._presence_index + 1) % len(PRESENCE_MESSAGES)
        try:
            await self.change_presence(
                activity=discord.Activity(type=discord.ActivityType.playing, name=message),
            )
        except discord.HTTPException as error:
            log.warning("não foi possível atualizar a rich presence: %s", error)

    @tasks.loop(time=datetime_time(hour=9, minute=0, tzinfo=BIRTHDAY_TIMEZONE))
    async def birthday_check(self):
        try:
            await self.announce_birthdays()
        except Exception:
            log.exception("falha na rotina diária de aniversários")

    async def announce_birthdays(self):
        async with self._birthday_lock:
            guild = self.get_guild(settings.guild_id)
            if guild is None:
                log.warning("guild %s indisponível para a rotina de aniversários", settings.guild_id)
                return
            channel = configured_channel(guild, "channel.warning")
            operator_role = configured_role(guild, "role.approved_member")
            if channel is None or operator_role is None:
                log.warning("canal warning ou cargo operador não configurado; aniversários ignorados")
                return

            today = datetime.now(BIRTHDAY_TIMEZONE).date()
            for record in database.list_members(guild.id):
                if not record.birthday:
                    continue
                try:
                    month, day = (int(part) for part in record.birthday.split("-", maxsplit=1))
                    if (month, day) != (today.month, today.day):
                        continue
                    user_id = int(record.user_id)
                except (TypeError, ValueError):
                    log.warning("aniversário inválido no cadastro do membro %s", record.user_id)
                    continue
                if database.has_birthday_announcement(guild.id, user_id, today.year):
                    continue

                member = guild.get_member(user_id)
                if member is None:
                    try:
                        member = await guild.fetch_member(user_id)
                    except discord.NotFound:
                        continue
                    except discord.HTTPException as error:
                        log.warning("não foi possível consultar membro %s para aniversário: %s", user_id, error)
                        continue
                if operator_role not in member.roles:
                    continue

                content = random.choice(BIRTHDAY_MESSAGES).format(mention=member.mention)
                try:
                    await channel.send(
                        content,
                        allowed_mentions=discord.AllowedMentions(
                            users=[member], roles=False, everyone=False, replied_user=False,
                        ),
                    )
                except discord.HTTPException as error:
                    log.warning("não foi possível publicar aniversário de %s: %s", user_id, error)
                    continue
                database.record_birthday_announcement(guild.id, user_id, today.year)
                log.info("mensagem de aniversário enviada para membro operador %s", user_id)

    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        try:
            await configure_join_access(member)
            log.info("fluxo de entrada configurado para %s", member.name)
        except discord.HTTPException as error:
            log.warning("falha ao configurar acesso de entrada para %s: %s", member.name, error)

    async def on_message(self, message: discord.Message):
        if not message.guild:
            await self.process_commands(message)
            return

        apply_channel = configured_channel(message.guild, "channel.apply")
        if apply_channel and message.channel.id == apply_channel.id:
            if self.user is None or message.author.id != self.user.id:
                try:
                    await message.delete()
                except discord.NotFound:
                    pass
                except discord.Forbidden:
                    log.warning("sem permissão para apagar mensagem não pertencente ao bot no canal apply")
                except discord.HTTPException as error:
                    log.warning("falha ao apagar mensagem não pertencente ao bot no canal apply (status %s)", error.status)
            return

        await self.process_commands(message)
        if message.author.bot or message.webhook_id is not None:
            return

        warning_channel = configured_channel(message.guild, "channel.warning")
        if warning_channel is None or message.channel.id != warning_channel.id:
            return

        try:
            await send_warning_editor(message)
        except discord.Forbidden:
            log.warning("sem permissão para criar thread privada ou adicionar o autor ao editor warning")
        except discord.HTTPException as error:
            log.warning("falha do Discord ao criar editor privado no canal warning (status %s)", error.status)

    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type is discord.InteractionType.component and interaction.data:
            try:
                await route_button(interaction)
            except Exception as error:
                log.exception("falha na interação %s", interaction.data.get("custom_id"))
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ {error}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ {error}", ephemeral=True)

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        original = getattr(error, "original", error)
        log.error("falha no comando %s", interaction.command.name if interaction.command else "desconhecido",
                  exc_info=(type(original), original, original.__traceback__))
        message = f"❌ {original}"
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


def main():
    try:
        settings.validate()
    except RuntimeError as error:
        log.error("%s", error)
        return
    bot = DefcomBot()
    bot.run(settings.token, log_handler=None)


if __name__ == "__main__":
    main()
