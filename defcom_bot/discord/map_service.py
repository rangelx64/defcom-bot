from __future__ import annotations

from ..storage import save_json
from .snapshot import build_snapshot


def render_markdown(snapshot: dict) -> str:
    guild = snapshot["guild"]
    lines = [f"# Mapa do servidor: {guild['name']}", "", f"Gerado em: {snapshot['generatedAt']}", "",
             f"## Categorias e canais ({sum(len(c['channels']) for c in snapshot['categories'])})", ""]
    for category in snapshot["categories"]:
        lines.extend([f"### {category['name']}", ""])
        for channel in category["channels"]:
            marker = "🔊" if channel["type"] == "voice" else "#"
            lines.append(f"- {marker} `{channel['name']}`")
        lines.append("")
    if snapshot["uncategorized"]:
        lines.extend(["### Sem categoria", ""])
        lines.extend(f"- `{channel['name']}` ({channel['type']})" for channel in snapshot["uncategorized"])
        lines.append("")
    lines.extend([f"## Cargos ({len(snapshot['roles'])})", ""])
    lines.extend(f"- `{role['name']}`" for role in snapshot["roles"])
    return "\n".join(lines) + "\n"


async def map_guild(guild):
    snapshot = build_snapshot(guild)
    save_json("mapa.json", snapshot)
    from ..storage import data_path
    path = data_path("MAPA.md")
    path.write_text(render_markdown(snapshot), encoding="utf-8")
    return snapshot, str(data_path("mapa.json")), str(path)


def map_summary(snapshot: dict, json_path: str, md_path: str) -> str:
    channels = sum(len(cat["channels"]) for cat in snapshot["categories"]) + len(snapshot["uncategorized"])
    return (f"✅ Mapa de **{snapshot['guild']['name']}** atualizado.\n"
            f"• Categorias: **{len(snapshot['categories'])}** · Canais: **{channels}** · Cargos: **{len(snapshot['roles'])}**\n"
            f"• `{json_path}`\n• `{md_path}`")
