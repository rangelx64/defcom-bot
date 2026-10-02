# Pegadinhas conhecidas

## Domínio

- Cargos existentes DEFCOM são somente leitura.
- Canais privados precisam dar acesso ao usuário bot explicitamente quando ele envia mensagens.
- Onboarding é substituição integral (PUT). O servidor precisa ter Community e cumprir requisitos do Discord para habilitá-lo.

## discord.py

- Components V2 estão disponíveis a partir de discord.py 2.6 e exigem LayoutView; mensagens V2 não devem misturar content ou embeds.
- Guild.edit_onboarding não é exposto publicamente pelo discord.py; o módulo usa discord.http.Route com o HTTP client autenticado. Revalidar o esquema do payload se a API Discord mudar.
- Botões persistentes precisam de custom_id e timeout None, e views devem ser registadas novamente no setup_hook após restart.
- Atribuição automática do cargo community exige Server Members Intent habilitado no Developer Portal.
- O fluxo de entrada também libera community nos canais apply, warning, general e media já configurados. A candidatura exige role.candidate; a aprovação reutiliza role.approved_member como cargo de operador.
- O acesso de operador reaproveita canais existentes e detecta salas privadas de liderança pelas sobrescritas atuais dos cargos configurados role.global_leader/role.squad_leader. Apply e candidaturas não recebem acesso do cargo aprovado; como community mantém acesso a apply, usa-se uma sobrescrita individual para negar apply e salas de liderança ao aprovado.
- A autorização do menu de membros exige correspondência entre os dados do líder no SQLite e os cargos atuais do Discord. Se o cargo de pelotão estiver ausente ou divergente, o squad leader perde acesso até os dados serem corrigidos.
- O menu grava apenas no cadastro SQLite. Remover alguém do cadastro não expulsa a pessoa nem remove cargos Discord.
- A candidatura aceita aniversário junto com idade no mesmo campo, pois o Discord limita a cinco campos por modal. Datas são armazenadas como MM-DD e apresentadas como DD/MM.
- `/install` é restrito ao dono real da guild (`guild.owner_id`). Cargos e canais funcionais são persistidos como IDs por servidor; não use nomes de cargos para conceder acesso. O cargo `staff_roles` pode conter vários IDs.
- O editor warning usa `messages` sem `message_content`; cria prévia em thread privada não-convidável, adiciona o autor e publica o final no canal pai só após clicar Publicar. Permissões do bot: Create Private Threads, Send Messages in Threads e Manage Messages (para adicionar membro à thread privada não-convidável, conforme discord.py). O `interaction_check` restringe a view ao autor original. Moderadores com Manage Threads ainda podem ver a thread; não afirmar privacidade contra moderadores.
- O `WarningEmbedModal` recebe `target_channel` da `WarningEmbedView` para reconstruir a view após cada edição; não remova esse repasse, pois o botão Publicar depende dele.
- A mensagem enviada para iniciar o editor no canal warning é apagada somente depois que a thread privada e a prévia são criadas com sucesso. O bot precisa de Manage Messages também para essa remoção.
- Ao publicar um aviso, o bot envia `@everyone` numa mensagem separada, tenta apagá-la após três segundos e apaga a thread privada do editor. Isso requer a permissão de mencionar everyone, Manage Messages e Manage Threads; falhas são reportadas sem desfazer o embed já publicado.
- Em discord.py, `Message.delete()` e `PartialMessage.delete()` não aceitam `reason`; não passe esse argumento ao remover a mensagem inicial ou a mensagem temporária de @everyone.
- Ao apagar a thread que contém a interação de Publicar, atualize a resposta efêmera antes de excluir a thread; não envie followup depois, pois a interação pode responder `Unknown Message`.
- No canal `channel.apply`, `on_message` apaga qualquer mensagem cujo autor não seja o próprio bot; isso também remove mensagens de outros bots/webhooks e exige Manage Messages no canal.
- A rich presence é iniciada uma vez em `on_ready` e alterna `PRESENCE_MESSAGES` com `tasks.loop(seconds=30)`; não inicie o loop em cada reconexão.
- Aniversários usam `MM-DD` no SQLite, conferem o cargo Discord `role.approved_member` no dia do envio e registram `guild_id/user_id/ano` em `birthday_announcements` para não duplicar. Rotina diária às 09:00 em America/Sao_Paulo, com catch-up único no início do processo.

## Graphify

- Não usar extração semântica/LLM nem export Obsidian. Se a CLI não estiver instalada, consultar relatório pré-gerado e registrar a limitação.
