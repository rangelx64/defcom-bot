# Convenções do projeto

- Python 3.11+, discord.py 2.6+ e python-dotenv.
- Módulos em defcom_bot/, separados por responsabilidade; contratos do domínio em models.py.
- Use discord.ext.commands.Cog, app_commands, discord.ui e dataclasses para manter comandos, interfaces e estado explícitos.
- Cargos são somente leitura; criar preserva existentes; alterações destrutivas pedem confirmação com botão; /aplicar só cria o que falta.
- Nomes de canal seguem minúsculas, sem acento, separados por hífen.
- Não use a palavra "clã" para descrever a equipe DEFCOM.
- Não invente ferramentas de lint/teste. Sintaxe: python -m compileall -q defcom_bot.
- .env é local. Não commitar segredos.
- Use graphify query enquanto graphify-out/graph.json existir. Se a CLI não estiver disponível, use o relatório e registre isso.
