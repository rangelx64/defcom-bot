# AGENTS.md: defcom_dc_bot

Contrato do projeto. Leia este arquivo e carregue os documentos complementares sob demanda.

## Projeto

Bot de gerenciamento do servidor Discord da DEFCOM. Mapeia categorias, canais, cargos e permissões; cria salas preservando a estrutura existente. Stack: Python 3.11+, `discord.py` 2.6+ e `python-dotenv`; dependências em `requirements.txt` e `pyproject.toml`.

## Regras de domínio

1. Cargos existentes são somente leitura: nunca criar, editar, renomear, apagar ou alterar cores. Atribuir cargos existentes a membros é permitido.
2. Criar nunca sobrescreve. Canais/categorias existentes são preservados.
3. Remover, renomear, mover canal ou remover categoria exige confirmação por botão.
4. `/aplicar` é create-only e idempotente.
5. O menu `/gerenciar-membros` só pode ser aberto por lideranças válidas: o
   `squad leader` administra apenas o pelotão indicado no SQLite e confirmado
   pelos cargos atuais do Discord; `global leader` administra todos.
6. O cadastro e as candidaturas ficam em SQLite. O menu não altera cargos nem
   expulsa membros; cargos do Discord são usados apenas para validar escopo.
7. Cargos e canais funcionais são configurados por ID no SQLite com `/install`;
   nunca use nomes de cargos como fonte de autorização. Só o dono da guild
   pode alterar essa configuração. O próprio Discord identifica o dono.

## Comandos

| Ação | Comando |
| --- | --- |
| Rodar | `python -m defcom_bot` |
| Atualizar mapa | Automaticamente ao iniciar ou `/mapear` |
| Publicar páginas | `/publicar-welcome` e `/publicar-apply` |
| Gerenciar membros | `/gerenciar-membros` |
| Configuração inicial | `/install` (dono do servidor) |
| Configurar onboarding | `/configurar-onboarding` |
| Renomear bot | `/renomear-bot` (dono do servidor, com confirmação) |
| Grafo | `./graphify-update.sh` |
| Consultar grafo | `graphify query "<pergunta>"` |
| Sintaxe | `python -m compileall -q defcom_bot` |

## Organização

- `defcom_bot/__main__.py`: inicialização, intents, eventos e registro guild-scoped.
- `defcom_bot/config.py`: configuração por ambiente em dataclass.
- `defcom_bot/models.py`: modelos de domínio tipados.
- `defcom_bot/content.py`: textos e estrutura desejada mantidos no código.
- `defcom_bot/storage.py`: persistência de snapshots e estado em `state/`.
- `defcom_bot/database.py`: cadastro de membros e candidaturas em SQLite.
- `state/`: arquivos gerados e runtime; não contém conteúdo de configuração.
- `defcom_bot/discord/`: comandos, interações, views, canais, permissões, mapa, plano declarativo e onboarding.

## Regras de trabalho

- Use `graphify query` antes de pesquisar o projeto enquanto o grafo existir. Se a ferramenta estiver indisponível, use `GRAPH_REPORT.md` e depois os arquivos relacionados, registrando a limitação.
- Nunca edite `graphify-out/` manualmente; regenere com `graphify-update.sh`.
- Nunca leia ou commite `.env`; somente `.env.example` pode ser versionado.
- Registrar novas pegadinhas em `.opencode/context/gotchas.md`.
- Status pendente em `PLANOS.md`; trabalho concluído acrescentado ao final de `HISTORICO.md`.
