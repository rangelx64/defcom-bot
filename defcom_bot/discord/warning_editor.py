from __future__ import annotations

import asyncio
from dataclasses import dataclass
from urllib.parse import urlparse

import discord
from discord import ui

from ..log import get_logger

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
            return await interaction.response.send_message("Somente o autor da mensagem pode editar esta prévia.", ephemeral=True)

        raw_color = self.color_hex.value.strip().removeprefix("#")
        if len(raw_color) != 6:
            return await interaction.response.send_message(
                "Informe a cor no formato hexadecimal de seis caracteres, como `#5865F2`.", ephemeral=True,
            )
        try:
            color = int(raw_color, 16)
        except ValueError:
            return await interaction.response.send_message(
                "A cor deve conter somente números e letras de A a F, como `#5865F2`.", ephemeral=True,
            )

        image = self.image_url.value.strip()
        if image:
            parsed = urlparse(image)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                return await interaction.response.send_message(
                    "A imagem precisa ser um link válido começando com `https://` ou `http://`.",
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
            return await interaction.response.send_message("Título e descrição não podem ficar vazios.", ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await self.editor_message.edit(
                content="Prévia do aviso. Somente o autor original pode editar ou publicar.",
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
            return await interaction.followup.send("Não foi possível atualizar a prévia. Tente novamente.", ephemeral=True)
        await interaction.followup.send("Prévia atualizada no canal. Você pode revisar, editar novamente ou publicar.", ephemeral=True)


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
                "Somente o autor da mensagem original pode usar este editor.", ephemeral=True,
            )
            return False
        return True

    @ui.button(label="Editar prévia", style=discord.ButtonStyle.primary)
    async def edit_preview(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.message is None:
            return await interaction.response.send_message("Não encontrei a mensagem da prévia.", ephemeral=True)
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
                "Edite a prévia e preencha o título e a descrição antes de publicar.", ephemeral=True,
            )
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await self.target_channel.send(
                embed=_build_embed(self.draft, self.author_name),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException as error:
            log.warning("falha ao publicar embed de aviso (status %s)", error.status)
            return await interaction.followup.send("Não foi possível publicar o aviso. Tente novamente.", ephemeral=True)

        ping_message = None
        ping_error = None
        try:
            ping_message = await self.target_channel.send(
                "@everyone",
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
        await interaction.edit_original_response(content=status)
        if editor_thread:
            try:
                await interaction.channel.delete(reason="Aviso publicado; encerrar tópico privado do editor")
            except discord.HTTPException as error:
                log.warning("aviso publicado, mas não foi possível apagar o tópico do editor (status %s)", error.status)
                try:
                    await interaction.edit_original_response(
                        content=f"{status} Não consegui apagar o tópico; confira a permissão Manage Threads."
                    )
                except discord.HTTPException:
                    log.warning("não foi possível atualizar a confirmação após falha ao apagar o tópico")
        elif interaction.message:
            await interaction.message.edit(
                content=f"Aviso publicado em {self.target_channel.mention}.", view=None,
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
    preview = discord.Embed(
        title="Prévia do aviso",
        description="Esta prévia é privada. Use **Editar prévia** para definir título, descrição, imagem e cor. O embed só aparecerá no canal warning depois de clicar em **Publicar**.",
        color=discord.Color.blurple(),
    )
    preview.set_footer(text=f"Autor: {author_name}")
    try:
        await thread.add_user(message.author)
        await thread.send(
            content="Editor privado do aviso. Somente o autor original pode editar ou publicar.",
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
