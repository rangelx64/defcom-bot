from __future__ import annotations

import discord
from discord.http import Route

from ..content import ONBOARDING
from .server_config import configured_channel, configured_role


def build_onboarding_plan(guild: discord.Guild):
    cfg = ONBOARDING
    missing = []
    defaults = []
    for key in cfg.get("defaultChannelKeys", []):
        channel = configured_channel(guild, key)
        if channel:
            defaults.append(channel)
        else:
            missing.append(f"canal {key}")
    prompts = []
    for prompt in cfg.get("prompts", []):
        options = []
        for option in prompt.get("options", []):
            roles = []
            channels = []
            for key in option.get("roleKeys", []):
                role = configured_role(guild, key)
                if role:
                    roles.append(role)
                else:
                    missing.append(f"cargo {key}")
            for key in option.get("channelKeys", []):
                channel = configured_channel(guild, key)
                if channel:
                    channels.append(channel)
                else:
                    missing.append(f"canal {key}")
            options.append({**option, "resolved_roles": roles, "resolved_channels": channels})
        prompts.append({**prompt, "resolved_options": options})
    return {"config": cfg, "default_channels": defaults, "prompts": prompts, "missing": sorted(set(missing))}


def render_onboarding_preview(plan) -> str:
    cfg = plan["config"]
    lines = ["**Prévia do onboarding**", f"• Ativado: **{'sim' if cfg.get('enabled', True) else 'não'}** · Modo: **{cfg.get('mode', 'default')}**",
             "• Canais padrão: " + (", ".join(ch.mention for ch in plan["default_channels"]) or "nenhum"), ""]
    for prompt in plan["prompts"]:
        lines.append(f"**{prompt['title']}** ({'única' if prompt.get('singleSelect') else 'múltipla'}, {'obrigatório' if prompt.get('required') else 'opcional'})")
        for option in prompt["resolved_options"]:
            targets = [*(f"cargo `{r.name}`" for r in option["resolved_roles"]), *(c.mention for c in option["resolved_channels"])]
            lines.append(f"• {option.get('emoji', '') + ' ' if option.get('emoji') else ''}{option['title']} → {', '.join(targets) or 'nenhum'}")
        lines.append("")
    return "\n".join(lines)


def _onboarding_payload(plan):
    cfg = plan["config"]
    prompts = []
    for prompt in plan["prompts"]:
        prompts.append({"title": prompt["title"], "single_select": prompt.get("singleSelect", False),
            "required": prompt.get("required", False), "in_onboarding": prompt.get("inOnboarding", True),
            "type": prompt.get("type", 0), "options": [{"title": opt["title"], "description": opt.get("description"),
                "emoji": {"name": opt.get("emoji")} if opt.get("emoji") else None,
                "role_ids": [str(role.id) for role in opt["resolved_roles"]],
                "channel_ids": [str(channel.id) for channel in opt["resolved_channels"]]} for opt in prompt["resolved_options"]]})
    return {"enabled": cfg.get("enabled", True), "mode": 1 if cfg.get("mode") == "advanced" else 0,
        "default_channel_ids": [str(channel.id) for channel in plan["default_channels"]], "prompts": prompts}


async def apply_onboarding(bot: discord.Client, guild: discord.Guild, plan):
    # discord.py does not yet expose Guild.edit_onboarding; use its authenticated HTTP route.
    route = Route("PUT", "/guilds/{guild_id}/onboarding", guild_id=guild.id)
    await bot.http.request(route, json=_onboarding_payload(plan))


async def ensure_community(bot: discord.Client, guild: discord.Guild):
    if "COMMUNITY" in guild.features:
        return
    rules = configured_channel(guild, "channel.warning")
    updates = configured_channel(guild, "channel.announcements")
    if not updates:
        raise RuntimeError("Canal de comunicados não configurado. Execute /install.")
    route = Route("PATCH", "/guilds/{guild_id}", guild_id=guild.id)
    payload = {"features": list(set((*guild.features, "COMMUNITY"))), "rules_channel_id": str(rules.id) if rules else None,
        "public_updates_channel_id": str(updates.id), "verification_level": 1,
        "explicit_content_filter": 2, "default_message_notifications": 1}
    try:
        await bot.http.request(route, json=payload)
    except discord.HTTPException as error:
        raise RuntimeError("O Discord exige ativar Community pelo fluxo manual em Configurações do Servidor. "
                           f"Detalhe: {error}") from error
