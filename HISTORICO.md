# HISTORICO.md — defcom_dc_bot

> Registro **append-only** do trabalho **concluído**, do mais antigo ao mais
> novo: sempre acrescentar no FIM. Itens chegam aqui **movidos** (não copiados)
> de `PLANOS.md`. Nunca leia este arquivo inteiro — navegue por seção
> (`mdocs list HISTORICO.md`).

## 1. Scaffold do repo e knowledge-stack

- **Data:** 2026-09-21
- **O que foi feito:**
  - `package.json` (ESM, pnpm), `.gitignore`, `.env.example`; `pnpm install`
    (`discord.js` v14, `dotenv`).
  - Documentos: `AGENTS.md`, `PLANOS.md`, `COMO_USAR.md`, `.opencode/context/*`,
    plugin graphify, `graphify-update.sh`.
- **Validação:** `pnpm install` concluído sem erro.
- **Arquivos:** `package.json`, `.gitignore`, `.env.example`, `AGENTS.md`,
  `PLANOS.md`, `COMO_USAR.md`, `.opencode/`, `graphify-update.sh`.

## 2. Núcleo do bot e `/mapear`

- **Data:** 2026-09-21
- **O que foi feito:**
  - `src/config.js`, `src/lib/logger.js`, `src/lib/confirm.js`.
  - `src/discord/snapshot.js` (leitura do guild: categorias, canais, cargos,
    overwrites) e `src/discord/map.js` (`/mapear` → `data/mapa.json` +
    `data/MAPA.md`).
  - `src/index.js`: client discord.js v14, intents Guilds+GuildMembers, registro
    guild-scoped de slash commands e flag `--map` (mapeia e encerra).
  - Grafo gerado: 111 nós / 117 arestas / 15 comunidades.
- **Validação:** `node --check` em todos os arquivos; smoke test de
  `buildSnapshot()` com guild fake (categoria, texto, voz, canal solto).
- **Arquivos:** `src/**`, `graphify-out/`.

## 3. Primeiro mapeamento no servidor real

- **Data:** 2026-09-21
- **O que foi feito:**
  - Corrigido login: `GuildMembers` (intent privilegiado) virou opcional
    (`ENABLE_MEMBER_INTENT`, padrão `false`) — o erro "Used disallowed intents"
    travava o login.
  - `/mapear` executado no servidor real: **4 categorias, 17 canais, 13 cargos**
    (guild `1347323931324977233`, "𝕯𝖊𝖋𝖊𝖓𝖘𝖊 𝕮𝖔𝖒𝖇𝖆𝖙 𝕲𝖗𝖔𝖚𝖕", 38 membros).
  - Slash commands registrados (guild-scoped).
- **Validação:** `pnpm map` concluiu; `data/mapa.json` e `data/MAPA.md` gerados.
- **Arquivos:** `src/index.js`, `src/config.js`, `.env.example`,
  `.opencode/context/{api,gotchas}.md`, `data/`.

## 4. Criação e gestão de salas (Fase 4–6)

- **Data:** 2026-09-21
- **O que foi feito:**
  - `src/discord/{names,presets,desired,plan,apply,create}.js` — normalização de
    nomes, presets de permissão (`publico`/`leitura`/`staff`/`privado`), leitura
    do `desired.json`, diff (dry-run) e aplicação create-only.
  - Comandos: `/plano`, `/aplicar`, `/criar-sala`, `/criar-categoria`,
    `/renomear-sala`, `/mover-sala`, `/remover-sala`, `/remover-categoria` —
    os destrutivos com confirmação por botão (`confirm.js`).
  - `data/desired.example.json` e `STAFF_ROLES` configurável.
  - 9 slash commands registrados no servidor.
- **Validação:** `node --check` em `src/**`; smoke test de `buildPlan` +
  `buildOverwrites` com guild fake (ignora existentes, cria novos, presets ok);
  `pnpm map` registrou os 9 comandos.
- **Arquivos:** `src/**`, `data/desired.example.json`, `COMO_USAR.md`,
  `.opencode/context/api.md`, `PLANOS.md`.

## 5. Páginas V2: welcome e candidatura

- **Data:** 2026-09-21
- **O que foi feito:**
  - `src/discord/{ui,welcome,application,review,publish,applyPlan}.js` —
    páginas em **Components V2** (Container/Section/Thumbnail/Separator),
    roteadas por `customId`.
  - `#welcome`: escolha de plataforma (PC/Console) concede `community` e mostra
    recomendações; `#apply`: modal (5 campos) → candidatura em `#candidaturas`
    (privado staff) → Aprovar concede `temporary`, Reprovar só registra.
  - Comandos `/publicar-welcome` e `/publicar-apply`; flag `pnpm publicar`.
  - `data/welcome.json`, `data/apply.json`, `data/applications.jsonl`,
    `data/published.json`.
- **Validação:** `node --check` em `src/**`; smoke test dos builders V2 (com/sem
  ícone); `pnpm publicar` publicou as páginas, criou `#candidaturas` (privado
  staff) e registrou 11 slash commands.
- **Arquivos:** `src/**`, `data/*.json`, `package.json`, `AGENTS.md`,
  `PLANOS.md`, `COMO_USAR.md`, `.opencode/context/*`.

## 6. Onboarding nativo (tela de entrada)

- **Data:** 2026-09-21
- **O que foi feito:**
  - `src/discord/onboarding.js` + `data/onboarding.json`: prompt "Qual sua
    plataforma?" → cargos `PC`/`Console`; canais padrão `general`, `media`,
    `loadout`, `apply`, `warning`; `enabled`, modo avançado.
  - Comando `/configurar-onboarding` (preview + confirmação) e flag
    `pnpm onboarding`.
  - 12 slash commands registrados.
- **Validação:** `node --check`; smoke test do plano (nomes → ids, missing=[]);
  aplicação bloqueada por `50013 Missing Permissions` — o bot está sem
  **Manage Server** (`me.permissions.ManageGuild = false`).
- **Arquivos:** `src/discord/onboarding.js`, `src/index.js`, `data/onboarding.json`,
  `package.json`, docs.

## 7. Fix de confirmação + Community/Onboarding

- **Data:** 2026-09-22
- **O que foi feito:**
  - Corrigido `src/lib/confirm.js`: usava `interaction.followup` (inexistente);
    o certo é `interaction.followUp`. Isso quebrava **todos** os comandos com
    confirmação (`/configurar-onboarding` e os destrutivos).
  - `ensureCommunity()` em `onboarding.js` + bloco `community` em
    `data/onboarding.json`; criado o canal `#avisos`.
  - Onboarding **configurado** com sucesso (`enabled:false`): prompt PC/Console
    + 7 canais padrão.
- **Validação:** `node --check`; `guild.editOnboarding` OK (prompts=1,
  defaults=7). Habilitar Community via API falha (`50001/50035`) — o usuário
  ativou **Community manualmente**; em seguida `pnpm onboarding` habilitou o
  onboarding (`enabled=true`, features `COMMUNITY`/`GUILD_ONBOARDING`).
- **Arquivos:** `src/lib/confirm.js`, `src/discord/onboarding.js`,
  `data/onboarding.json`, docs.

## 8. Fix de acesso do bot ao #candidaturas

- **Data:** 2026-09-22
- **O que foi feito:**
  - Candidatura falhava com `Missing Access` (50001/50013): o `#candidaturas`
    (preset `staff`) negava `@everyone` e não dava acesso ao bot; e o bot não
    conseguia se conceder (não via o canal / hierarquia do próprio cargo).
  - `ensureStaffChannel`: passa a incluir **overwrite de membro** do bot
    (`me.id` com View+Send) na criação e a **reparar** canal existente quando o
    bot já vê mas não envia.
  - Recriado/ajustado o `#candidaturas` no servidor (View liberado; o bot
    auto-concedeu Send).
- **Validação:** perms do bot view/send = true; envio e remoção de container V2
  de candidatura no canal real com sucesso.
- **Arquivos:** `src/discord/application.js`, `.opencode/context/gotchas.md`,
  `PLANOS.md`.

## 9. Candidatura única (anti-duplicidade)

- **Data:** 2026-09-22
- **O que foi feito:**
  - `data/applications.jsonl` passa a registrar também a **decisão** da staff
    (`{ type: "decision", messageId, decision, reviewerId }`).
  - `findPendingApplication(userId)` + bloqueio em `apply:start` e no submit:
    quem tem candidatura **pendente** não abre o modal nem envia outra.
  - `findApplication` ignora linhas de decisão.
- **Validação:** `node --check`; smoke test com `applications.jsonl` fake
  (decidida→libera, pendente→bloqueia, inexistente→libera).

## 10. Renomear o bot para DFCENTCOMM

- **Data:** 2026-09-22
- **O que foi feito:**
  - Flag `--rename <nome>` / `pnpm rename`; usuário do bot alterado para
    **DFCENTCOMM** (`client.user.setUsername`) e cargo renomeado manualmente
    pelo dono para `DFCENTCOMM`.
  - Referências atualizadas em `AGENTS.md`, `COMO_USAR.md`, `PLANOS.md` e
    `.opencode/context/architecture.md`.
- **Validação:** `c.user.username === "DFCENTCOMM"`; `pnpm map` mostra o cargo
  `DFCENTCOMM` na posição 8.

## 11. Reescrita modular em Python

- **Data:** 2026-10-01
- **O que foi feito:**
  - Reescrita dos fluxos e comandos do bot em Python 3.11+ / discord.py 2.6+,
    com módulos de domínio, dataclasses, views persistentes, Components V2,
    modals, slash commands e configuração por ambiente.
  - Mantidos os formatos de dados em `data/` e as regras de cargos somente
    leitura, criação preservadora, `/aplicar` idempotente e confirmação das
    alterações destrutivas.
  - Removidos código e manifestos de dependências JavaScript; adicionados
    `pyproject.toml` e `requirements.txt`.
- **Validação:** pendente em `PLANOS.md`.
- **Limitação:** `graphify query` e `graphify-update.sh` não puderam ser usados
  neste ambiente porque a CLI `graphify` não está instalada; artefatos do grafo
  ainda refletem a implementação anterior.

## 12. Configuração embutida no código

- **Data:** 2026-10-01
- **O que foi feito:**
  - Textos e configurações de welcome, candidatura e onboarding passaram para
    `defcom_bot/content.py`; a estrutura desejada também ficou definida em
    `DESIRED` no mesmo módulo.
  - Removido `data/`; snapshots existentes foram preservados em `state/`, que
    também recebe os arquivos gerados e o estado operacional do bot.
- **Validação:** compilação sintática local; imports/runtime seguem pendentes
  porque `discord.py` não está instalado no ambiente.

## 13. Cadastro e gerenciamento de membros

- **Data:** 2026-10-01
- **O que foi feito:**
  - Criado `/gerenciar-membros` com menu privado para adicionar, remover,
    promover e mover membros entre pelotões.
  - O acesso de squad leader é limitado ao pelotão registrado no SQLite e
    confirmado pelos cargos atuais no Discord. Global leader tem acesso global.
  - Criado banco SQLite para membros e candidaturas. O formulário de aplicação
    também coleta aniversário junto com idade no mesmo campo do modal.
  - Os botões do menu alteram somente o cadastro interno; cargos e presença no
    servidor não são modificados.
- **Validação:** compilação sintática local. Validação runtime pendente porque
  `discord.py` não está instalado neste ambiente.

## 14. Instalação por IDs de cargos e canais

- **Data:** 2026-10-01
- **O que foi feito:**
  - Criado `/install`, acessível somente pelo dono real da guild, com seletores
    nativos para cargos e canais. As configurações são gravadas no SQLite por
    servidor e podem ser alteradas pelo mesmo comando.
  - Substituída a configuração `STAFF_ROLES` por nomes por uma lista de IDs no
    SQLite. As checagens de líder global, líder de pelotão e pelotão também
    consultam IDs configurados.
  - Welcome, candidatura, revisão, onboarding e presets de staff passaram a
    resolver cargos e canais configurados por ID.
- **Validação:** compilação sintática local; não foi feita conexão com Discord.

## 15. Inicialização sem flags

- **Data:** 2026-10-01
- **O que foi feito:**
  - Removidas as flags CLI. `python -m defcom_bot` é o único comando para
    iniciar o processo; o snapshot atualiza automaticamente ao conectar.
  - Publicação, onboarding e mapeamento manual continuam disponíveis como
    comandos slash. Renomear o bot foi movido para `/renomear-bot`, restrito
    ao dono do servidor e protegido por confirmação.
- **Validação:** compilação sintática local; não foi feita conexão com Discord.

## 16. Texto e confirmação da candidatura

- **Data:** 2026-10-01
- **O que foi feito:**
  - Reformulada a introdução da candidatura com foco em companheirismo, deveres,
    direitos e crescimento em equipe, mantendo funcionamento e requisitos.
  - Adicionada confirmação obrigatória dos termos no modal. O candidato precisa
    digitar `CONCORDO` para enviar.
  - Experiência e motivação foram reunidas em um campo para respeitar o limite
    de cinco campos do modal sem perder essas respostas.
- **Validação:** compilação sintática local.

## 17. Consulta aos termos da candidatura

- **Data:** 2026-10-01
- **O que foi feito:**
  - Adicionado o botão **Ler os termos** à página de candidatura.
  - O botão abre uma mensagem privada com os compromissos de participação
    ativa no clã, contribuição ao crescimento e respeito ao nome e ao logo.
- **Validação:** compilação sintática local.

## 18. Estilo visual da candidatura

- **Data:** 2026-10-01
- **O que foi feito:**
  - Reorganizada a página em seções de apresentação, etapas, requisitos e ação.
  - Removidos emojis dos botões e dos cartões de candidatura e avaliação.
- **Validação:** compilação sintática local.

## 19. Formatação automática do canal de avisos

- **Data:** 2026-10-01
- **O que foi feito:**
  - Adicionado listener para mensagens novas no canal warning selecionado por
    `/install`; ignora bots, webhooks, outros canais e mensagens sem texto.
  - Integração opcional com Groq para corrigir português e sugerir título e
    formatação Markdown. A chave é lida de `GROQ_API_KEY`; sem ela, o intent de
    conteúdo não é ativado e nenhuma chamada externa ocorre.
  - O bot responde com embed, desativa menções e preserva a mensagem original.
    O conteúdo enviado ao provedor não inclui nome nem ID do autor.
- **Validação:** compilação sintática local; integração real depende de chave,
  permissões do canal e Message Content Intent habilitado no portal.

## 20. Provedor de IA hospedado pelo Hugging Face

- **Data:** 2026-10-01
- **O que foi feito:**
  - Substituída a integração anterior pela API hospedada de Inference Providers
    do Hugging Face, sem execução local do modelo.
  - A autenticação agora usa `HF_TOKEN`, e o modelo configurável usa `HF_MODEL`
    (padrão `Qwen/Qwen2.5-7B-Instruct`).
  - Documentados créditos mensais limitados e os requisitos do token.
- **Validação:** checagem sintática; chamada à API depende de token Hugging Face.

## 21. Uso da cota gratuita do Hugging Face

- **Data:** 2026-10-01
- **O que foi feito:**
  - Definido inicialmente `google/gemma-2-2b-it:cheapest` como padrão para
    priorizar o provedor de menor custo disponível para o modelo.
  - Limitada a entrada a 6.000 caracteres e a saída a 400 tokens para reduzir
    o consumo da cota mensal gratuita informada pelo Hugging Face.
  - Após incompatibilidade HTTP 400 com o modelo inicial, selecionado
    `Qwen/Qwen2.5-7B-Instruct:cheapest` e removido `response_format` obrigatório;
    a formatação JSON permanece solicitada no prompt.
- **Validação:** compilação sintática local; disponibilidade e custo final
  dependem dos provedores e preços vigentes no Hugging Face.

## 22. SDK OpenAI para Hugging Face

- **Data:** 2026-10-01
- **O que foi feito:**
  - Substituída a chamada HTTP manual pelo `AsyncOpenAI`, apontando para o
    endpoint OpenAI-compatible dos Inference Providers do Hugging Face.
  - Adicionada dependência `openai` ao pyproject.toml e requirements.txt.
  - Desativados retries automáticos para evitar consumo duplicado de créditos;
    logs continuam omitindo corpo de erro, token e conteúdo submetido.
- **Validação:** compilação sintática e diff check; chamada real depende de
  token e instalação atualizada das dependências.

## 23. Editor privado de embeds no canal warning

- **Data:** 2026-10-01
- **O que foi feito:**
  - Removida a integração de IA, suas variáveis e a dependência do SDK OpenAI.
  - Mensagens novas no canal warning configurado iniciam uma DM ao autor com
    botão para abrir modal de título, descrição, imagem por URL, cor e rodapé.
  - O embed final é enviado somente na conversa privada e inclui no footer o
    autor da mensagem original. A mensagem no canal não é editada nem removida.
  - O fluxo requer Message Content Intent habilitado no Developer Portal.
- **Validação:** compilação sintática; teste interativo requer bot conectado.

## 24. Prévia e publicação do embed no canal warning

- **Data:** 2026-10-01
- **O que foi feito:**
  - Alterado o editor para funcionar no próprio canal, sem DM.
  - Cada mensagem inicia uma prévia pública editável; somente o autor original
    pode atualizar a prévia e clicar em Publicar.
  - Publicar finaliza a mesma mensagem de prévia, remove os botões e mantém no
    footer o autor da mensagem original.
  - Removido `message_content`: o bot detecta novas mensagens, sem ler o texto.
- **Validação:** compilação sintática e construção local de modal/view.

## 25. Prévia do aviso em thread privada

- **Data:** 2026-10-01
- **O que foi feito:**
  - Movida a prévia para thread privada criada sob o canal warning; o autor é
    adicionado como membro e somente ele pode usar os botões.
  - O botão Publicar envia o embed final ao canal pai e desativa o editor
    privado. A mensagem original continua preservada.
  - Registrada a limitação do Discord: moderadores com Manage Threads podem
    acessar threads privadas.
- **Validação:** compilação sintática; teste no servidor requer permissões de
  Create Private Threads, Manage Messages e Send Messages in Threads.
