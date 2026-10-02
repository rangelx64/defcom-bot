# COMO_USAR.md: defcom_dc_bot

Manual prático do bot DEFCOM, reescrito em Python com discord.py.

## Instalação e configuração

Requer Python 3.11+. Instale as dependências no Python local e copie .env.example para .env:

    python -m pip install --user -r requirements.txt
    cp .env.example .env

Preencha DISCORD_TOKEN e GUILD_ID. Habilite **Server Members Intent** no Developer Portal; ele é necessário para atribuir o cargo community automaticamente quando alguém entra.

## Rodar

    python -m defcom_bot

Ao conectar, o bot atualiza automaticamente o snapshot do servidor em `state/`. As demais ações administrativas são comandos slash e não são executadas automaticamente durante o carregamento.

A atividade do bot alterna a cada 30 segundos entre mensagens motivacionais e convites para enviar candidatura à DEFCOM. Os textos ficam em `PRESENCE_MESSAGES` no arquivo `defcom_bot/content.py`.

A rotina de aniversário verifica o cadastro SQLite às 9h (horário de São Paulo) e também faz uma checagem ao iniciar. Só anuncia quem tem aniversário cadastrado e ainda possui o cargo configurado como membro aprovado/operador. As mensagens são publicadas em warning, marcam somente o aniversariante e não se repetem para a mesma pessoa no mesmo ano. O código combina 10 aberturas, 10 votos e 10 encerramentos, formando 1.000 variações; os textos estão em `BIRTHDAY_*` no `content.py`.

## Comandos slash

| Comando | Efeito |
| --- | --- |
| /mapear | Gera state/mapa.json e state/MAPA.md |
| /plano | Mostra dry-run da estrutura definida em defcom_bot/content.py |
| /aplicar | Cria somente o que falta |
| /gerenciar-membros | Abre o menu privado de cadastro de membros |
| /publicar-welcome | Publica/fixa Components V2 no canal welcome configurado |
| /publicar-apply | Publica/fixa Components V2 no canal apply configurado |
| /configurar-onboarding | Preview, confirmação e atualização do onboarding |
| /criar-sala | Cria canal de texto/voz com preset |
| /criar-categoria | Cria categoria |
| /renomear-sala | Renomeia canal após confirmação |
| /mover-sala | Move canal após confirmação |
| /remover-sala | Remove canal após confirmação |
| /remover-categoria | Remove categoria após confirmação |
| /install | Configura IDs de cargos e canais, somente para o dono do servidor |
| /renomear-bot | Altera o nome do bot após confirmação, somente para o dono do servidor |

## Configuração inicial

Depois de iniciar o bot no servidor, o dono do servidor Discord deve executar `/install` e selecionar os cargos e canais nos menus. Os IDs ficam no SQLite por guild, sem depender dos nomes dos cargos. Configure os cargos de líder global, líder de pelotão, pelotões, staff, candidato, membro aprovado/operador, comunidade e plataformas; configure também welcome, apply, candidaturas, general, media, loadout, warning, arts e avisos. O dono do servidor é autorizado pelo próprio Discord e não precisa de cargo configurado.

## Estrutura declarativa

/plano e /aplicar usam DESIRED em defcom_bot/content.py. /aplicar não altera nem remove recursos existentes. Edite esse modelo no código para declarar categorias e canais.

## Páginas interativas

#welcome: botões PC/Console, atribuição do cargo configurado e recomendações por canais configurados.

#apply: a página usa seções separadas para apresentação, etapas e requisitos, sem emojis. Mensagens que não forem do próprio bot são apagadas automaticamente nesse canal, então o bot precisa de Manage Messages. O botão **Ler os termos** mostra os compromissos da candidatura em uma mensagem privada. O modal pergunta nome, idade e aniversário (DD/MM), experiência e motivação, disponibilidade e confirmação dos termos. Para confirmar, é necessário digitar `CONCORDO`. Idade e aniversário compartilham um campo e experiência e motivação também, respeitando o limite de cinco itens do modal. A candidatura vai para o canal candidates configurado e atribui candidate. A staff aprova (atribui o cargo existente de membro aprovado/operador e remove candidate) ou reprova (remove candidate e envia mensagem motivadora no privado) por botões. Uma candidatura pendente bloqueia duplicatas. Operadores recebem acesso aos canais existentes, exceto apply, candidaturas e salas privadas identificadas pelas permissões atuais dos cargos de liderança. Textos e campos ficam em defcom_bot/content.py; candidaturas e membros são registrados em SQLite.

## Gerenciamento de membros

O comando /gerenciar-membros mostra um embed privado com botões para adicionar, remover, promover e mover membros de pelotão. As alterações são feitas no cadastro SQLite, não expulsam a pessoa e não alteram cargos do Discord. Remoções exigem confirmação.

O global leader pode administrar todos os registros. Um squad leader precisa ter os cargos configurados por `/install`, um registro SQLite com patente squad leader e um pelotão que corresponda ao cargo configurado para esse pelotão. Esse líder só vê e administra membros do próprio pelotão. Ao cadastrar alguém, o pelotão do squad leader é aplicado automaticamente.

O banco fica em state/defcom.sqlite3. Para a candidatura, a data é armazenada como mês e dia; um membro aprovado é incluído/atualizado no cadastro com seu aniversário.

Onboarding usa ONBOARDING em defcom_bot/content.py e os IDs escolhidos no `/install`; requer Community e permissões Manage Server. O endpoint é substituição integral; o slash command apresenta prévia e confirmação.

## Variáveis

- Server Members Intent: deve estar habilitado no Developer Portal para o evento de entrada.
- STATE_DIR=state, LOG_LEVEL=info: diretório de estado (inclui o SQLite) e nível de log.

## Editor privado de embeds de aviso

Configure o canal warning pelo `/install`. Para cada mensagem nova nesse canal, o bot cria uma thread privada e adiciona o autor; a prévia e o editor aparecem nessa thread. Depois que o editor é criado com sucesso, a mensagem inicial é apagada automaticamente. O autor edita título, descrição, URL de imagem, cor hexadecimal e texto adicional de rodapé. **Publicar** envia o embed final ao canal warning, dispara um `@everyone` em mensagem separada (apagada após três segundos) e apaga a thread privada do editor. O footer identifica automaticamente o autor da mensagem original. O bot usa apenas o intent de novas mensagens e não precisa ler o conteúdo da mensagem para abrir o editor. Precisa de Create Private Threads, Send Messages in Threads, Manage Messages (adicionar o autor e apagar mensagens), Manage Threads (apagar a thread) e permissão para mencionar everyone.

Os textos de welcome, candidatura e onboarding são editados diretamente em defcom_bot/content.py. state/ contém apenas arquivos gerados e estado operacional.

Cargos existentes são somente leitura. Criações preservam o estado existente; operações destrutivas exigem confirmação.
