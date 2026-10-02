"""Text and declarative configuration kept in source control with the bot."""

PRESENCE_MESSAGES = (
    "Juntos somos mais fortes. Evolua com a DEFCOM",
    "Disciplina, respeito e união: venha para a DEFCOM",
    "Candidate-se e faça parte da equipe DEFCOM",
    "Seu próximo passo começa no apply. Candidate-se",
    "Construa sua história ao lado da DEFCOM",
    "A equipe cresce quando cada integrante contribui",
)

BIRTHDAY_OPENINGS = (
    "Hoje o destaque é seu, {mention}: feliz aniversário!",
    "{mention}, hoje a equipe celebra a sua vida e a caminhada que construímos juntos.",
    "Chegou o seu dia, {mention}, e a DEFCOM não ia deixar a data passar em branco.",
    "Feliz aniversário, {mention}! Hoje é dia de reconhecer a pessoa e o integrante que você é.",
    "{mention}, mais um ciclo começa, e a DEFCOM comemora esse momento com você.",
    "A data de hoje tem nome: {mention}. Feliz aniversário, com carinho de toda a DEFCOM.",
    "{mention}, que bom poder celebrar mais um ano da sua história com a nossa equipe.",
    "Hoje a nossa equipe tem um motivo especial para comemorar: o seu aniversário, {mention}.",
    "Parabéns pelo seu dia, {mention}. A DEFCOM deseja que esta nova etapa comece muito bem.",
    "{mention}, receba o abraço de toda a equipe neste dia especial. Feliz aniversário!",
)

BIRTHDAY_WISHES = (
    "Que o novo ciclo venha cheio de saúde, conquistas e bons momentos dentro e fora do jogo.",
    "Que você encontre bons desafios, boas companhias e muitos motivos para se orgulhar do caminho.",
    "Desejamos um ano leve, com planos saindo do papel e muitas histórias boas para contar.",
    "Que nunca faltem coragem para seguir em frente, parceria nos dias difíceis e alegria nas vitórias.",
    "Que cada objetivo alcançado abra espaço para sonhos ainda maiores e novas oportunidades.",
    "Esperamos que seu ano seja marcado por evolução, amizade sincera e momentos que valham a pena.",
    "Que a vida retribua toda a dedicação que você coloca nas coisas e nas pessoas ao seu redor.",
    "Desejamos saúde para aproveitar cada etapa, serenidade para os desafios e energia para suas conquistas.",
    "Que este próximo capítulo traga experiências marcantes e muitas razões para continuar acreditando.",
    "Que seja um ano de crescimento, respeito, união e vitórias construídas com quem está ao seu lado.",
)

BIRTHDAY_CLOSINGS = (
    "Conte com a equipe e aproveite muito o seu dia.",
    "Obrigado por fazer parte da nossa história. Estamos juntos.",
    "Hoje a comemoração é sua; aproveite cada instante.",
    "Seguimos lado a lado, com respeito, parceria e vontade de crescer.",
    "Receba os melhores votos de toda a família DEFCOM.",
    "Que venham boas memórias e muitas conquistas pela frente.",
    "A equipe fica feliz por ter você conosco. Parabéns!",
    "Aproveite a data perto de quem faz bem para você.",
    "Um grande abraço de todos nós e um excelente novo ciclo.",
    "Feliz aniversário e que este seja apenas o começo de uma fase incrível.",
)

BIRTHDAY_MESSAGES = tuple(
    f"{opening} {wish} {closing}"
    for opening in BIRTHDAY_OPENINGS
    for wish in BIRTHDAY_WISHES
    for closing in BIRTHDAY_CLOSINGS
)

WELCOME = {
    "accentColor": "#2B2D31",
    "title": "𝕯𝖊𝖋𝖊𝖓𝖘𝖊 𝕮𝖔𝖒𝖇𝖆𝖙 𝕲𝖗𝖔𝖚𝖕",
    "intro": "Somos um time de jogos militares. Aqui é equipe, família e disciplina dentro e fora do jogo. Que bom ter você aqui!",
    "platformQuestion": "Primeiro, qual é a sua plataforma?",
    "footer": "Dúvidas? Chame a staff. Dá uma lida também em #warning.",
    "platforms": {
        "pc": {
            "label": "PC", "emoji": "🖥️", "headline": "Setup para PC",
            "message": "Bora, {name}! Estas são as salas que combinam com quem joga no PC:",
            "recommend": ["apply", "general", "media", "warning"],
        },
        "console": {
            "label": "Console", "emoji": "🎮", "headline": "Setup para Console",
            "message": "Bora, {name}! Estas são as salas que combinam com quem joga no Console:",
            "recommend": ["apply", "general", "media", "warning"],
        },
    },
}

APPLICATION = {
    "accentColor": "#2B2D31",
    "title": "Candidatura: DEFCOM",
    "intro": (
        "A DEFCOM é muito mais do que um grupo de jogos online. Somos uma família "
        "de irmãos acima de tudo. Aqui, temos deveres e também direitos. Se você "
        "procura companheirismo, respeito e vontade de evoluir junto, queremos conhecer você."
    ),
    "steps": [
        "Leia os requisitos abaixo", "Clique em **Iniciar candidatura**",
        "Responda o formulário (leva ~2 min)", "A staff avalia e te dá um retorno",
    ],
    "requirements": [
        "Respeito ao time e à hierarquia", "Microfone e Discord em dia",
        "Disponibilidade para treinos", "Vontade de evoluir junto com a equipe",
    ],
    "terms": [
        "Participar ativamente do clã, incluindo atividades, treinos e comunicações da equipe.",
        "Contribuir para o crescimento do clã e agir com respeito, preservando o bom nome e a imagem do nosso logo.",
        "Respeitar os demais integrantes, a hierarquia, os direitos e os deveres de cada membro.",
    ],
    "modalTitle": "Candidatura DEFCOM",
    "fields": [
        {"id": "name", "label": "Nome / apelido", "style": "short", "placeholder": "Como te chamamos?"},
        {"id": "age_birthday", "label": "Idade e aniversário (DD/MM)", "style": "short", "placeholder": "Ex.: 22 anos, aniversário em 17/04"},
        {"id": "experience_motivation", "label": "Experiência e motivação", "style": "paragraph", "placeholder": "Conte sua experiência com jogos e por que quer fazer parte da equipe."},
        {"id": "availability", "label": "Disponibilidade", "style": "short", "placeholder": "Dias e horários"},
        {"id": "agreement", "label": "Concordo com os termos", "style": "short", "placeholder": "Digite CONCORDO para confirmar"},
    ],
}

APH_GUIDE = {
    "title": "Guia rápido de APH | ACE Medical",
    "description": (
        "Procedimento de referência para o sistema médico ACE usado pela equipe. "
        "Priorize a segurança da área, comunique o estado do paciente e siga a ordem de estabilização."
    ),
    "sections": [
        {
            "name": "1. Segurança e avaliação",
            "value": (
                "• Antes de tratar, procure cobertura e confirme que a área está segura.\n"
                "• Informe pelo rádio a posição, quantidade de feridos e quem está atendendo.\n"
                "• Verifique sangramento, respiração, batimentos, SpO₂, pressão e vias aéreas.\n"
                "• Se houver mais de um ferido, priorize quem precisa de intervenção imediata."
            ),
        },
        {
            "name": "2. Sangramento e volume sanguíneo",
            "value": (
                "• Estanque todos os sangramentos primeiro; confira novamente após cada tratamento.\n"
                "• O objetivo deste procedimento é deixar a hemorragia em Classe 1.\n"
                "• Se continuar acima de Classe 1, administre salina e reavalie os sinais vitais.\n"
                "• Não considere o paciente estabilizado só porque o sangramento visível parou."
            ),
        },
        {
            "name": "3. Respiração, vias aéreas e SpO₂",
            "value": (
                "• SpO₂ abaixo de 80% pode atrasar a recuperação do paciente.\n"
                "• Durante a RCP, acompanhe a SpO₂ e busque chegar a 90%.\n"
                "• Parada respiratória: tente **Lift Chin**. Se não resolver, use tubo e máscara de O₂.\n"
                "• Verifique e remova vômito/obstruções quando a interação do mod permitir.\n"
                "• Reavalie a respiração depois de cada intervenção."
            ),
        },
        {
            "name": "4. Parada cardiorrespiratória",
            "value": (
                "1. Administre epinefrina conforme o procedimento do servidor.\n"
                "2. Coloque a máscara de O₂ e mantenha as vias aéreas livres.\n"
                "3. Faça RCP e acompanhe a SpO₂ até alcançar aproximadamente 90%.\n"
                "4. Quando respiração e batimentos voltarem, não pare: continue estabilizando e monitorando."
            ),
        },
        {
            "name": "5. Pressão e medicação",
            "value": (
                "• Pressão alta: administre morfina e aguarde a pressão estabilizar.\n"
                "• Depois da estabilização, use amônia conforme o fluxo ensinado no servidor.\n"
                "• Evite repetir medicações sem reavaliar o paciente; confira sinais vitais após cada etapa."
            ),
        },
        {
            "name": "6. Checklist antes de levantar",
            "value": (
                "Confirme todos os pontos:\n"
                "• Hemorragia em Classe 1;\n"
                "• Respiração e batimentos funcionando;\n"
                "• SpO₂ adequada;\n"
                "• Pressão normalizada;\n"
                "• Vias aéreas livres.\n\n"
                "Após levantar, observe se o quadro piora e mantenha o rádio informado."
            ),
        },
        {
            "name": "Dicas de equipe",
            "value": (
                "• Um integrante atende; outro faz segurança e comunica a situação.\n"
                "• Peça kit, maca ou evacuação cedo quando necessário.\n"
                "• Diga em voz alta o que já foi tratado para evitar medicação duplicada.\n"
                "• Não abandone cobertura para tratar sob fogo; mova o ferido para uma posição segura quando possível."
            ),
        },
        {
            "name": "Para decorar",
            "value": "**Sangue → Classe 1 → SpO₂ → Parada? Tratar → Pressão → Amônia → Reavaliar → Levantar**",
        },
    ],
    "footer": (
        "Guia para o ACE Medical no Arma Reforger; itens, nomes e limiares podem variar conforme a versão/configuração do mod."
    ),
}

ONBOARDING = {
    "enabled": True,
    "mode": "advanced",
    "community": {"enable": True},
    "defaultChannelKeys": ["channel.general", "channel.media", "channel.loadout", "channel.welcome", "channel.apply", "channel.arts", "channel.warning"],
    "prompts": [{
        "title": "Qual sua plataforma?", "singleSelect": True, "required": True,
        "inOnboarding": True,
        "options": [
            {"title": "PC", "emoji": "🖥️", "description": "Jogo no PC", "roleKeys": ["role.pc"]},
            {"title": "Console", "emoji": "🎮", "description": "Jogo no Console", "roleKeys": ["role.console"]},
        ],
    }],
}

# Não havia desired.json ativo; o arquivo de exemplo não era aplicado pelo bot.
# Mantenha vazio para preservar o comportamento atual até definir uma estrutura.
DESIRED = {"categories": []}

# Os níveis são dados do cadastro interno; não criam nem editam cargos Discord.
MEMBER_RANKS = ("candidate", "operator", "squad leader", "global leader")
PLATOONS = ("alfa", "bravo", "charlie", "delta")
