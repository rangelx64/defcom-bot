# Arquitetura

O bot mantém um eixo de leitura (snapshot JSON/Markdown) e um eixo de escrita segura (plano create-only e criação sob demanda). Comandos são app_commands guild-scoped; interfaces usam discord.ui, views persistentes, modals e Components V2 (LayoutView).

| Módulo | Responsabilidade |
| --- | --- |
| __main__.py | Bot, intents, lifecycle, CLI e eventos |
| config.py / models.py | Configuração tipada e modelos de domínio |
| discord/commands.py | Slash commands e fluxo de gestão |
| discord/member_management.py | Menu de membros, escopo por liderança, pelotão e aniversário |
| discord/install.py | Wizard `/install` e persistência de IDs funcionais por guild |
| discord/server_config.py | Resolução de cargos e canais pelos IDs do SQLite |
| discord/channels.py | Busca, criação, edição e permissões |
| discord/snapshot.py, map_service.py | Snapshot e /mapear |
| discord/planning.py | /plano, /aplicar e idempotência |
| discord/interactions.py | Welcome, candidatura, revisão, publicação e views |
| discord/onboarding.py | Plano e payload de onboarding |
| storage.py / database.py | Snapshots JSON e cadastro SQLite |

Fluxos: /mapear grava snapshot em state/; /plano compara DESIRED de content.py com o servidor; /aplicar cria apenas o ausente. Welcome oferece escolha de plataforma e cargo community. Apply abre modal, grava candidatura em #candidaturas e a staff decide por botões; aprovação atribui temporary. A entrada no servidor pode atribuir community quando o intent está habilitado. Operações destrutivas passam por confirmação efêmera.

`/gerenciar-membros` exibe somente os registros autorizados ao líder. A autorização combina o cargo do Discord com patente e pelotão no SQLite. Um squad leader fica limitado ao próprio pelotão; global leader tem acesso global. A interface altera somente o cadastro SQLite.
