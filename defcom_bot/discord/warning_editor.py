from __future__ import annotations

import asyncio
from dataclasses import dataclass
from urllib.parse import urlparse

import discord
from discord import ui

from ..log import get_logger
from .presentation import card, result

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class WarningDraft:
    title: str
    description: str
    image_url: str
    color: int
    extra_footer: str


def _build_embed(draft: WarningDraft, author_name: str) -> discord.Embed:
    embed = discord.Embed(
        title=draft.title,
        description=draft.description,
        color=discord.Color(draft.color),
    )
    embed.set_author(name="DEFCOM | Avisos e comunicados")
    if draft.image_url:
        embed.set_image(url=draft.image_url)
    footer = f"Autor: {author_name[:256]}"
    if draft.extra_footer:
        footer = f"{draft.extra_footer} | {footer}"
    embed.set_footer(text=footer[:2048])
    return embed


class WarningEmbedModal(ui.Modal, title="Editar prévia do aviso"):
    def __init__(self, *, owner_id: int, author_name: str, editor_message: discord.Message,
                 target_channel: discord.TextChannel, draft: WarningDraft | None = None):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.author_name = author_name
        self.editor_message = editor_message
        self.target_channel = target_channel
        self.embed_title = ui.TextInput(
            label="Título", placeholder="Título do aviso", max_length=256,
            default=draft.title if draft else None, required=True,
        )
        self.description = ui.TextInput(
            label="Descrição", placeholder="Escreva o conteúdo do aviso",
            style=discord.TextStyle.paragraph, max_length=4000,
            default=draft.description if draft else None, required=True,
        )
        self.image_url = ui.TextInput(
            label="Imagem (URL, opcional)", placeholder="https://exemplo.com/imagem.png",
            max_length=500, default=draft.image_url if draft and draft.image_url else None,
            required=False,
        )
        self.color_hex = ui.TextInput(
            label="Cor em hexadecimal", placeholder="#5865F2", default=f"#{draft.color:06X}" if draft else "#5865F2",
            max_length=7, required=True,
        )
        self.footer = ui.TextInput(
            label="Texto adicional no rodapé (opcional)",
            placeholder="O autor original será acrescentado automaticamente",
            max_length=1500, default=draft.extra_footer if draft and draft.extra_footer else None,
            required=False,
        )
        for field in (self.embed_title, self.description, self.image_url, self.color_hex, self.footer):
            self.add_item(field)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message(embed=card("Edição restrita", "Somente o autor da mensagem original pode editar esta prévia.", tone="error"), ephemeral=True)

        raw_color = self.color_hex.value.strip().removeprefix("#")
        if len(raw_color) != 6:
            return await interaction.response.send_message(
                embed=card("Cor inválida", "Informe a cor no formato hexadecimal de seis caracteres, como `#5865F2`.", tone="warning"), ephemeral=True,
            )
        try:
            color = int(raw_color, 16)
        except ValueError:
            return await interaction.response.send_message(
                embed=card("Cor inválida", "Use apenas números e letras de A a F, como `#5865F2`.", tone="warning"), ephemeral=True,
            )

        image = self.image_url.value.strip()
        if image:
            parsed = urlparse(image)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                return await interaction.response.send_message(
                    embed=card("Link de imagem inválido", "Use um endereço válido começando com `https://` ou `http://`.", tone="warning"),
                    ephemeral=True,
                )

        draft = WarningDraft(
            title=self.embed_title.value.strip(),
            description=self.description.value.strip(),
            image_url=image,
            color=color,
            extra_footer=self.footer.value.strip(),
        )
        if not draft.title or not draft.description:
            return await interaction.response.send_message(embed=card("Preencha o aviso", "Título e descrição não podem ficar vazios.", tone="warning"), ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await self.editor_message.edit(
                content=None,
                embed=_build_embed(draft, self.author_name),
                view=WarningEmbedView(
                    owner_id=self.owner_id,
                    author_name=self.author_name,
                    target_channel=self.target_channel,
                    draft=draft,
                ),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException as error:
            log.warning("falha ao atualizar prévia do aviso (status %s)", error.status)
            return await interaction.followup.send(embed=card("Prévia não atualizada", "Não foi possível atualizar a prévia. Tente novamente.", tone="error"), ephemeral=True)
        await interaction.followup.send(embed=result("Prévia atualizada", "Revise o aviso, edite novamente se precisar ou publique quando estiver pronto."), ephemeral=True)


class WarningEmbedView(ui.View):
    def __init__(self, *, owner_id: int, author_name: str, target_channel: discord.TextChannel,
                 draft: WarningDraft | None = None):
        super().__init__(timeout=900)
        self.owner_id = owner_id
        self.author_name = author_name
        self.target_channel = target_channel
        self.draft = draft

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                embed=card("Edição restrita", "Somente o autor da mensagem original pode usar este editor.", tone="error"), ephemeral=True,
            )
            return False
        return True

    @ui.button(label="Editar prévia", style=discord.ButtonStyle.primary)
    async def edit_preview(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.message is None:
            return await interaction.response.send_message(embed=card("Prévia indisponível", "Não encontrei a mensagem da prévia. Abra o editor novamente.", tone="error"), ephemeral=True)
        await interaction.response.send_modal(WarningEmbedModal(
            owner_id=self.owner_id,
            author_name=self.author_name,
            editor_message=interaction.message,
            target_channel=self.target_channel,
            draft=self.draft,
        ))

    @ui.button(label="Publicar", style=discord.ButtonStyle.success)
    async def publish(self, interaction: discord.Interaction, button: ui.Button):
        if self.draft is None:
            return await interaction.response.send_message(
                embed=card("Aviso incompleto", "Edite a prévia e preencha o título e a descrição antes de publicar.", tone="warning"), ephemeral=True,
            )
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await self.target_channel.send(
                embed=_build_embed(self.draft, self.author_name),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException as error:
            log.warning("falha ao publicar embed de aviso (status %s)", error.status)
            return await interaction.followup.send(embed=card("Aviso não publicado", "Não foi possível publicar o aviso. Tente novamente.", tone="error"), ephemeral=True)

        ping_message = None
        ping_error = None
        try:
            ping_message = await self.target_channel.send(
                "@everyone",
                embed=card("Novo aviso", "A equipe publicou um comunicado no canal.", tone="warning"),
                allowed_mentions=discord.AllowedMentions(everyone=True, users=False, roles=False),
            )
            await asyncio.sleep(3)
            await ping_message.delete()
        except discord.HTTPException as error:
            ping_error = error
            log.warning("falha ao enviar ou apagar menção do aviso (status %s)", error.status)

        editor_thread = isinstance(interaction.channel, discord.Thread)
        if ping_error:
            status = (
                "Aviso publicado, mas houve uma falha no @everyone ou na remoção da mensagem da menção. "
                "Confira as permissões de mencionar everyone e de gerenciar mensagens."
            )
        else:
            status = "Aviso publicado; @everyone enviado e mensagem da menção apagada."
        if editor_thread:
            status += " O tópico do editor será apagado."

        # Confirme a ação antes de remover a thread que originou a interação.
        await interaction.edit_original_response(content=None, embed=card("Aviso publicado", status, tone="success" if not ping_error else "warning"))
        if editor_thread:
            try:
                await interaction.channel.delete(reason="Aviso publicado; encerrar tópico privado do editor")
            except discord.HTTPException as error:
                log.warning("aviso publicado, mas não foi possível apagar o tópico do editor (status %s)", error.status)
                try:
                    await interaction.edit_original_response(
                        content=None,
                        embed=card("Aviso publicado com pendência", f"{status}\n\nNão consegui apagar o tópico; confira a permissão Gerenciar Tópicos.", tone="warning"),
                    )
                except discord.HTTPException:
                    log.warning("não foi possível atualizar a confirmação após falha ao apagar o tópico")
        elif interaction.message:
            await interaction.message.edit(
                content=None, embed=result("Aviso publicado", f"O aviso foi publicado em {self.target_channel.mention}."), view=None,
            )


async def send_warning_editor(message: discord.Message) -> None:
    if not isinstance(message.channel, discord.TextChannel):
        return
    author_name = message.author.display_name[:256]
    thread = await message.channel.create_thread(
        name=f"editar-aviso-{str(message.id)[-8:]}",
        type=discord.ChannelType.private_thread,
        invitable=False,
        reason="Criar editor privado para aviso",
    )
    preview = card(
        "Editor de avisos",
        "Esta prévia é privada. Use **Editar prévia** para definir título, descrição, imagem e cor. O aviso só aparecerá no canal após clicar em **Publicar**.",
        tone="brand",
        footer="DEFCOM • Prévia privada; somente o autor original pode publicar",
    )
    preview.set_footer(text=f"Autor: {author_name}")
    try:
        await thread.add_user(message.author)
        await thread.send(
            content=None,
            embed=preview,
            view=WarningEmbedView(
                owner_id=message.author.id,
                author_name=author_name,
                target_channel=message.channel,
            ),
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except Exception:
        try:
            await thread.delete(reason="Falha ao preparar editor privado do aviso")
        except discord.HTTPException:
            pass
        raise

    try:
        await message.delete()
    except discord.HTTPException as error:
        log.warning(
            "editor do aviso criado, mas não foi possível apagar a mensagem inicial %s (status %s)",
            message.id,
            error.status,
        )
