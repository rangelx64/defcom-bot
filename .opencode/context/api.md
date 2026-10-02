# API Discord e integrações

O cliente usa discord.py 2.6+ e intents guilds; members é opcional e exige Server Members Intent no portal. Slash commands usam app_commands registrados na guild configurada. Comandos administrativos exigem Manage Server por padrão.

Components V2 usam discord.ui.LayoutView, Container, Section, TextDisplay, Separator, ActionRow e botões; views persistentes não dependem de collectors. O formulário é discord.ui.Modal com até cinco campos.

O cadastro de membros e o fluxo de candidaturas usam SQLite em `state/defcom.sqlite3`, sem dependência adicional além da biblioteca padrão. O modal de candidatura combina idade e aniversário no campo de texto, respeitando o limite de cinco componentes; o aniversário é normalizado para mês-dia no banco.

O menu `/gerenciar-membros` revalida a autorização em cada interação. Líderes de pelotão precisam ter o cargo `squad leader`, registro correspondente no banco e cargo do pelotão correspondente no Discord. `global leader` tem escopo global. Os botões atualizam somente o cadastro e nunca alteram cargos ou removem pessoas do servidor.

Onboarding nativo usa PUT /guilds/{guild_id}/onboarding via cliente HTTP autenticado do discord.py porque não há método público Guild.edit_onboarding. O payload segue a API Discord e substitui a configuração existente; o slash command mostra preview e pede confirmação.

Permissões de canal são PermissionOverwrite; cargos são resolvidos por nome e nunca criados/editados. Manage Roles pode ser necessário para aplicar overwrites, mas isso não autoriza editar cargos.

Variáveis: DISCORD_TOKEN, GUILD_ID, ENABLE_MEMBER_INTENT, STATE_DIR, LOG_LEVEL. Cargos e canais são selecionados pelo `/install` e guardados como IDs no SQLite por guild.

O editor de avisos usa `on_message` com o intent `messages` (não habilitar `message_content`, pois o texto não é lido). Para mensagem nova no canal warning configurado, cria uma thread privada não-convidável, adiciona o autor e publica a prévia nessa thread. O bot precisa Create Private Threads, Send Messages in Threads e Manage Messages (necessário para adicionar um membro a uma thread privada não-convidável, conforme discord.py). O modal tem título, descrição, URL de imagem, cor e footer adicional; cada submissão atualiza a prévia privada. Publicar envia o embed final ao canal pai e remove os controles da prévia. O footer inclui o autor original. A mensagem original permanece intacta. Moderadores com Manage Threads podem visualizar threads privadas.
