# PLANOS.md: defcom_dc_bot

> Fonte de verdade das pendências. O trabalho concluído é registrado no final de HISTORICO.md.

## Estado atual

- [x] Bot reescrito modularmente em Python com discord.py 2.6+.
- [x] Comandos slash, eventos, permissões, confirmação por botões, Components V2, modal, candidatura, revisão, mapa, plano declarativo e onboarding portados.
- [x] Removidas as flags de execução. O snapshot é atualizado durante o carregamento; operações administrativas ficam em comandos slash.
- [x] Manifestos e módulos do runtime JavaScript removidos.
- [x] Compilação sintática local (`python -m compileall -q defcom_bot`).
- [x] Configurações textuais e estrutura declarativa movidas para `content.py`;
      removido o diretório `data/` (snapshots preservados em `state/`).
- [x] Menu `/gerenciar-membros` com controle por cargo, pelotão e cadastro SQLite.
- [x] SQLite para membros e fluxo de candidaturas; formulário pede idade e
      aniversário no campo combinado.
- [x] `/install` privado ao dono do servidor, com seleção de IDs de cargos e
      canais, persistidos no SQLite por guild.
- [x] Editor privado em thread vinculada ao warning; modal personalizável,
      acesso do autor e publicação final no canal pai. Sem IA ou DM.
- [x] Autorização de liderança, staff de candidatura, cargos atribuídos no
      fluxo de aplicação e canais funcionais resolvidos por ID.
- [ ] Revisar diferenças de comportamento após validação runtime.
- [ ] Validar o payload de onboarding nativo contra o servidor real.
- [ ] Fazer smoke check interativo e publicar as páginas no servidor DEFCOM.
- [ ] Preencher docs/ com estrutura atual do servidor.

> Limitações desta sessão: a instalação runtime do bot não foi executada nesta
> sessão. `graphify` também não está instalado;
> os artefatos gerados ainda descrevem a implementação JavaScript anterior.

## Estado persistido em runtime

- state/mapa.json e state/MAPA.md: snapshot do servidor.
- defcom_bot/content.py: textos e estrutura declarativa.
- state/defcom.sqlite3: cadastros de membros e candidaturas.
- state/published.json: IDs das páginas publicadas.

## Regras permanentes

1. Cargos são somente leitura; atribuir cargos existentes é permitido.
2. Preservar recursos já existentes.
3. Operações destrutivas só após confirmação por botão.
4. /aplicar cria somente o que falta.
5. Sem LLM no graphify e sem export para Obsidian.

## Execução e dependências

- Requer Python 3.11+.
- Instalação: python -m pip install -e .
- Execução: python -m defcom_bot
- Comandos administrativos: `/mapear`, `/publicar-welcome`, `/publicar-apply`, `/configurar-onboarding` e `/renomear-bot`.
- Dependências: discord.py e python-dotenv, declaradas em pyproject.toml/requirements.txt.

## Próximo passo sugerido

Executar `/install` no servidor Discord com o dono da guild e conferir as
seleções de IDs; depois publicar as páginas e revisar o onboarding.
