from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ..config import settings
from .channels import (create_category, create_channel, delete_category, delete_channel,
                       find_category, find_channel, move_channel, rename_channel)
from .aph_guide import build_aph_guide_embed
from .interactions import publish_pages
from .install import InstallView, install_embed
from .map_service import map_guild, map_summary
from .member_management import MemberManagementView, actor_scope, roster_embed
from .onboarding import apply_onboarding, build_onboarding_plan, ensure_community, render_onboarding_preview
from .planning import apply_plan, build_plan, load_desired, render_plan
from .presentation import card, result
from .server_config import configured_channel
from .ui import confirm_action

MANAGE = app_commands.default_permissions(manage_guild=True)


async def _defer(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)


class Management(commands.Cog):
    """Comandos de gerenciamento do servidor."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="install", description="Configuração inicial dos cargos e canais do bot.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def install(self, interaction: discord.Interaction):
        if interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message(
                embed=card("Acesso restrito", "Somente o dono do servidor Discord pode configurar o bot.", tone="error"), ephemeral=True,
            )
        await interaction.response.send_message(
            embed=install_embed(interaction.guild), view=InstallView(interaction.user.id), ephemeral=True,
        )

    @app_commands.command(name="renomear-bot", description="Altera o nome de exibição do bot no Discord.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.describe(nome="Novo nome para o bot")
    async def renomear_bot(self, interaction: discord.Interaction, nome: str):
        if interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message(
                embed=card("Acesso restrito", "Somente o dono do servidor Discord pode alterar o nome do bot.", tone="error"), ephemeral=True,
            )
        await _defer(interaction)
        confirmed = await confirm_action(
            interaction,
            title=f"Alterar o nome do bot para {nome!r}?",
            description="Essa mudança afeta a conta do bot no Discord.",
            confirm_label="Alterar nome",
        )
        if not confirmed:
            return await interaction.followup.send(embed=card("Alteração cancelada", "O nome do bot permaneceu igual.", tone="warning"), ephemeral=True)
        if self.bot.user is None:
            return await interaction.followup.send(embed=card("Bot indisponível", "Não consegui identificar a conta do bot.", tone="error"), ephemeral=True)
        await self.bot.user.edit(username=nome)
        await interaction.followup.send(embed=result("Nome atualizado", f"O bot agora aparece como **{nome}**."), ephemeral=True)

    @app_commands.command(name="mapear", description="Mapeia o servidor (categorias, canais e cargos). Somente leitura.")
    @MANAGE
    async def mapear(self, interaction: discord.Interaction):
        await _defer(interaction)
        snapshot, json_path, md_path = await map_guild(interaction.guild)
        await interaction.followup.send(embed=card("Mapeamento concluído", map_summary(snapshot, json_path, md_path), tone="success"), ephemeral=True)

    @app_commands.command(name="plano", description="Mostra o que seria criado a partir da estrutura definida no código (dry-run).")
    @MANAGE
    async def plano(self, interaction: discord.Interaction):
        await _defer(interaction)
        await interaction.followup.send(embed=card("Plano de estrutura", render_plan(build_plan(interaction.guild, load_desired()))[:4000]), ephemeral=True)

    @app_commands.command(name="aplicar", description="Cria o que falta na estrutura definida no código (create-only, idempotente).")
    @MANAGE
    async def aplicar(self, interaction: discord.Interaction):
        await _defer(interaction)
        result = await apply_plan(interaction.guild, build_plan(interaction.guild, load_desired()))
        if result.created == 0 and not result.failed:
            message = "Não há alterações necessárias. A estrutura existente está em dia."
        else:
            lines = [f"Itens criados: **{result.created}**."]
            if result.failed:
                lines += ["", f"Falhas: **{len(result.failed)}**"]
                lines.extend(f"• `{item['action'].get('name')}`: {item['error']}" for item in result.failed)
            message = "\n".join(lines)
        await interaction.followup.send(embed=card("Aplicação do plano", message, tone="success" if not result.failed else "warning"), ephemeral=True)

    @app_commands.command(name="gerenciar-membros", description="Abre o menu privado de gerenciamento do cadastro de membros.")
    @app_commands.guild_only()
    async def gerenciar_membros(self, interaction: discord.Interaction):
        scope = actor_scope(interaction)
        if scope is None:
            return await interaction.response.send_message(
                embed=card("Acesso restrito", "Este menu é exclusivo para global leaders e squad leaders cadastrados no próprio pelotão.", tone="error"),
                ephemeral=True,
            )
        await interaction.response.send_message(
            embed=roster_embed(interaction.guild, scope),
            view=MemberManagementView(interaction.user.id),
            ephemeral=True,
        )

    @app_commands.command(name="publicar-welcome", description="Publica a página de boas-vindas no canal configurado.")
    @MANAGE
    async def publicar_welcome(self, interaction: discord.Interaction):
        await _defer(interaction)
        await publish_pages(interaction.guild, welcome=True, apply=False)
        channel = configured_channel(interaction.guild, "channel.welcome")
        await interaction.followup.send(embed=result("Boas-vindas publicadas", f"A página foi publicada e fixada em {channel.mention}."), ephemeral=True)

    @app_commands.command(name="publicar-apply", description="Publica a página de candidatura no canal configurado.")
    @MANAGE
    async def publicar_apply(self, interaction: discord.Interaction):
        await _defer(interaction)
        await publish_pages(interaction.guild, welcome=False, apply=True)
        channel = configured_channel(interaction.guild, "channel.apply")
        await interaction.followup.send(embed=result("Candidatura publicada", f"A página foi publicada e fixada em {channel.mention}. O canal privado da staff está configurado."), ephemeral=True)

    @app_commands.command(name="publicar-guia-aph", description="Publica o guia de APH do ACE Medical no canal configurado.")
    @MANAGE
    @app_commands.guild_only()
    async def publicar_guia_aph(self, interaction: discord.Interaction):
        await _defer(interaction)
        channel = configured_channel(interaction.guild, "channel.aph")
        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            return await interaction.followup.send(
                embed=card("Canal de APH não configurado", "O dono do servidor deve selecionar o canal existente no `/install`.", tone="error"),
                ephemeral=True,
            )
        await channel.send(embed=build_aph_guide_embed())
        await interaction.followup.send(embed=result("Guia de APH publicado", f"O guia foi enviado para {channel.mention}."), ephemeral=True)

    @app_commands.command(name="configurar-onboarding", description="Configura o Onboarding nativo (preview + confirmação).")
    @MANAGE
    async def configurar_onboarding(self, interaction: discord.Interaction):
        await _defer(interaction)
        plan = build_onboarding_plan(interaction.guild)
        if plan["missing"]:
            return await interaction.followup.send(embed=card("Configuração incompleta", f"Não encontrei: {', '.join(plan['missing'])}. Confira a estrutura existente e tente novamente.", tone="error"), ephemeral=True)
        preview = render_onboarding_preview(plan)
        ok = await confirm_action(interaction, title="Aplicar o Onboarding?", description=f"{preview}\n\nIsso **substitui** o onboarding atual.", confirm_label="Aplicar")
        if not ok:
            return
        try:
            if plan["config"].get("community", {}).get("enable"):
                await ensure_community(self.bot, interaction.guild)
            await apply_onboarding(self.bot, interaction.guild, plan)
            await interaction.followup.send(embed=result("Onboarding configurado", "Confira o resultado em Configurações do Servidor → Onboarding."), ephemeral=True)
        except Exception as error:
            await interaction.followup.send(embed=card("Falha no onboarding", f"Não foi possível aplicar a configuração. Confira a permissão Gerenciar Servidor.\n\nDetalhe: {error}", tone="error"), ephemeral=True)

    @app_commands.command(name="criar-sala", description="Cria um canal de texto ou voz.")
    @MANAGE
    @app_commands.describe(nome="Nome da sala", tipo="Texto ou voz", categoria="Categoria (nome)", preset="Permissões", cargos="Cargos com acesso, separados por vírgula", topico="Tópico do canal de texto")
    @app_commands.choices(tipo=[app_commands.Choice(name="texto", value="text"), app_commands.Choice(name="voz", value="voice")],
        preset=[app_commands.Choice(name=n, value=n) for n in ("publico", "leitura", "staff", "privado")])
    async def criar_sala(self, interaction: discord.Interaction, nome: str, tipo: app_commands.Choice[str], categoria: str | None = None,
                         preset: app_commands.Choice[str] | None = None, cargos: str = "", topico: str | None = None):
        await _defer(interaction)
        value = preset.value if preset else "publico"
        channel = await create_channel(interaction.guild, name=nome, type=tipo.value, category_name=categoria,
            preset=value, roles=[role.strip() for role in cargos.split(",") if role.strip()], topic=topico)
        parent = f" em **{channel.category.name}**" if channel.category else ""
        await interaction.followup.send(embed=result("Canal criado", f"**{channel.name}** foi criado{parent}.\nPreset de permissões: **{value}**."), ephemeral=True)

    @app_commands.command(name="criar-categoria", description="Cria uma categoria.")
    @MANAGE
    async def criar_categoria(self, interaction: discord.Interaction, nome: str):
        await _defer(interaction)
        created, channel = await create_category(interaction.guild, nome)
        msg = f"✅ Categoria `{channel.name}` criada." if created else f"ℹ️ Categoria `{channel.name}` já existe."
        await interaction.followup.send(embed=card("Categoria existente" if not created else "Categoria criada", f"A categoria **{channel.name}** {'já existia e foi preservada.' if not created else 'foi criada.'}.", tone="info" if not created else "success"), ephemeral=True)

    @app_commands.command(name="renomear-sala", description="Renomeia um canal (com confirmação).")
    @MANAGE
    async def renomear_sala(self, interaction: discord.Interaction, nome: str, novo_nome: str):
        await _defer(interaction)
        channel = find_channel(interaction.guild, nome)
        if not channel:
            raise ValueError(f'Canal "{nome}" não encontrado.')
        if await confirm_action(interaction, title=f"Renomear `{channel.name}` → `{novo_nome}`?", description="O canal mantém ID, permissões e histórico.", confirm_label="Renomear"):
            await rename_channel(interaction.guild, nome, novo_nome)
            await interaction.followup.send(embed=result("Canal renomeado", f"O canal agora se chama **{novo_nome}**."), ephemeral=True)

    @app_commands.command(name="mover-sala", description="Move um canal para outra categoria (com confirmação).")
    @MANAGE
    async def mover_sala(self, interaction: discord.Interaction, nome: str, categoria: str | None = None):
        await _defer(interaction)
        channel = find_channel(interaction.guild, nome)
        if not channel:
            raise ValueError(f'Canal "{nome}" não encontrado.')
        parent = find_category(interaction.guild, categoria) if categoria else None
        target = parent.name if parent else categoria or "sem categoria"
        if await confirm_action(interaction, title=f"Mover `{channel.name}`?", description=f"Destino: **{target}**.", confirm_label="Mover"):
            await move_channel(interaction.guild, nome, categoria)
            await interaction.followup.send(embed=result("Canal movido", f"O canal foi movido para **{target}**."), ephemeral=True)

    @app_commands.command(name="remover-sala", description="Remove um canal (exige confirmação).")
    @MANAGE
    async def remover_sala(self, interaction: discord.Interaction, nome: str):
        await _defer(interaction)
        channel = find_channel(interaction.guild, nome)
        if not channel:
            raise ValueError(f'Canal "{nome}" não encontrado.')
        if await confirm_action(interaction, title=f"Remover `{channel.name}`?", description="⚠️ Ação irreversível. O canal e o histórico serão apagados.", confirm_label="Remover"):
            await delete_channel(interaction.guild, nome)
            await interaction.followup.send(embed=result("Canal removido", f"O canal **{nome}** foi removido."), ephemeral=True)

    @app_commands.command(name="remover-categoria", description="Remove uma categoria (exige confirmação).")
    @MANAGE
    async def remover_categoria(self, interaction: discord.Interaction, nome: str):
        await _defer(interaction)
        category = find_category(interaction.guild, nome)
        if not category:
            raise ValueError(f'Categoria "{nome}" não encontrada.')
        if await confirm_action(interaction, title=f"Remover categoria `{category.name}`?", description=f"⚠️ {len(category.channels)} canal(is) ficarão sem categoria (não são apagados).", confirm_label="Remover"):
            await delete_category(interaction.guild, nome)
            await interaction.followup.send(embed=result("Categoria removida", f"A categoria **{nome}** foi removida. Os canais foram preservados."), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Management(bot))
