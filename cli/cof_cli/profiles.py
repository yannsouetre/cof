"""The personality-profile entries of `cof psyche propose` (Yann, 4 November 2026: popular profiles must not be forgotten):
`--mbti <type>` (a Myers-Briggs four-letter type), `--enneagram <n>` (an Enneagram type, 1–9, an optional wing like 4w5) and
`--big-five O=80,C=35,E=20,A=70,N=60` (OCEAN scores, 0–100, or the file's psyche.json › traits annex). Like the horoscope
(zodiac.py) these are an author's shorthand: a small static table of `value` / `taste` / `habit` / `fear` / `want` / `need`
candidates, gists in English and French, strength 50, stability `shifting`, a tag (`mbti:<type>`, `enneagram:<n>`,
`bigfive:<trait>-<high|low>`) and a source (`mbti`, `enneagram`, `big-five`) — proposed « to review by the author », like every
candidate. Nothing here is a node kind nor a field of the format; the nodes are ordinary nodes once accepted.
« MBTI » is a registered trademark: the four-letter types are used descriptively, no affiliation — user-facing text says
« Myers-Briggs type (four letters) »; `mbti` is only an identifier in the code."""
from __future__ import annotations

import json
import re
from pathlib import Path

# ---- Myers-Briggs four-letter types ------------------------------------------------------------------------------------------
MBTI_TYPES = ("intj", "intp", "entj", "entp", "infj", "infp", "enfj", "enfp", "istj", "isfj", "estj", "esfj", "istp", "isfp", "estp", "esfp")

# type → [(kind, en, fr), …]: common descriptive readings, three or four candidates per type, in the reading order of RFC 0004; no pronoun, so that any character fits
_MBTI = {
    "intj": [
        ("value", "Competence: an idea is worth what it does once it is built, and a plan is judged by whether it survives contact with reality.",
                  "La compétence : une idée vaut ce qu'elle donne une fois construite, et un plan se juge à sa survie au contact du réel."),
        ("taste", "Loves long-range planning and a quiet evening with a hard problem; dislikes small talk and meetings without an agenda.",
                  "Aime planifier loin et passer une soirée tranquille devant un problème difficile ; n'aime ni le bavardage ni les réunions sans ordre du jour."),
        ("habit", "Builds a private plan years ahead and says little about it until it is nearly done.",
                  "Construit en privé un plan sur plusieurs années et en dit peu avant qu'il soit presque abouti."),
        ("fear", "Fears wasted effort: a year spent on something that was never going to work.",
                 "Craint l'effort gaspillé : une année passée sur ce qui ne pouvait pas marcher."),
    ],
    "intp": [
        ("value", "Understanding: a question is worth more than a quick answer, and an explanation with a gap in it is not yet an explanation.",
                  "La compréhension : une question vaut mieux qu'une réponse rapide, et une explication qui a un trou n'en est pas encore une."),
        ("taste", "Loves thought experiments, tidy systems and long digressions; dislikes rules that nobody can justify.",
                  "Aime les expériences de pensée, les systèmes bien faits et les longues digressions ; n'aime pas les règles que personne ne sait justifier."),
        ("habit", "Opens three projects of the mind at once and forgets to eat while chasing the most interesting one.",
                  "Ouvre trois chantiers de l'esprit à la fois et oublie de manger en poursuivant le plus intéressant."),
        ("fear", "Fears the mistake found in public, on a subject claimed to be understood.",
                 "Craint l'erreur découverte en public, sur un sujet qu'on prétendait maîtriser."),
    ],
    "entj": [
        ("value", "Drive: a goal worth having deserves a plan, a deadline and someone willing to answer for it.",
                  "L'impulsion : un objectif qui vaut la peine mérite un plan, une échéance et quelqu'un qui accepte d'en répondre."),
        ("taste", "Loves a clear objective, a well-run room and an argument that settles the matter; dislikes dithering and vague ownership.",
                  "Aime un objectif clair, une réunion bien menée et un argument qui tranche ; n'aime ni les atermoiements ni les responsabilités floues."),
        ("habit", "Takes charge of a stalled group within minutes, hands out the tasks and sets the date.",
                  "Prend en main un groupe qui s'enlise en quelques minutes, répartit les tâches et fixe la date."),
        ("want", "Wants to lead something large enough to be worth the effort.",
                 "Veut diriger quelque chose d'assez grand pour que l'effort en vaille la peine."),
    ],
    "entp": [
        ("value", "Open debate: every idea should be tested hard, including the ones everybody already agrees with.",
                  "Le débat ouvert : toute idée mérite d'être mise à l'épreuve, y compris celles sur lesquelles tout le monde est déjà d'accord."),
        ("taste", "Loves a clever argument, a new gadget and a plan nobody has tried; bored by routine and repetition.",
                  "Aime l'argument astucieux, le gadget nouveau et le plan que personne n'a essayé ; s'ennuie dans la routine et la répétition."),
        ("habit", "Argues the opposite side for sport, then is surprised when someone takes it personally.",
                  "Défend le camp adverse pour le plaisir, puis s'étonne que quelqu'un le prenne mal."),
        ("fear", "Fears a fixed role with no room left to try anything new.",
                 "Craint l'enfermement dans un rôle figé, sans plus de place pour essayer du nouveau."),
    ],
    "infj": [
        ("value", "Meaning: what one does should serve something larger than the day, and people deserve to be understood, not just managed.",
                  "Le sens : ce qu'on fait doit servir quelque chose de plus grand que la journée, et les gens méritent d'être compris, pas seulement gérés."),
        ("taste", "Loves quiet conversations that go deep, long walks and books that change how one sees; tires quickly in a crowd.",
                  "Aime les conversations calmes qui vont au fond, les longues marches et les livres qui changent le regard ; se fatigue vite dans la foule."),
        ("habit", "Senses the mood of a room before anyone speaks, and keeps a private opinion until trust is there.",
                  "Perçoit l'humeur d'une pièce avant que quiconque parle, et garde son avis pour soi tant que la confiance n'est pas là."),
        ("need", "Needs time alone to recover after giving a lot, and rarely asks for it.",
                 "A besoin de temps seul pour récupérer après avoir beaucoup donné, et le demande rarement."),
    ],
    "infp": [
        ("value", "Authenticity: a life should match what one actually believes, even when it costs some comfort.",
                  "L'authenticité : une vie doit correspondre à ce qu'on croit vraiment, même si cela coûte un peu de confort."),
        ("taste", "Loves poetry, old songs and a rainy afternoon with a book; dislikes cruelty, noise and being rushed.",
                  "Aime la poésie, les vieilles chansons et un après-midi de pluie avec un livre ; n'aime ni la cruauté, ni le bruit, ni la précipitation."),
        ("habit", "Keeps a notebook of half-finished stories and feelings, and shows it to almost nobody.",
                  "Tient un carnet d'histoires et de sentiments inachevés, et ne le montre presque à personne."),
        ("fear", "Fears betraying a deeply held value, and never forgiving the slip.",
                 "Craint de trahir une valeur profonde et de ne jamais se pardonner ce faux pas."),
    ],
    "enfj": [
        ("value", "Growth: people become more than they thought they could when someone believes in them out loud.",
                  "L'épanouissement : les gens deviennent plus qu'ils ne pensaient pouvoir l'être quand quelqu'un croit en eux à voix haute."),
        ("taste", "Loves bringing people together, a well-laid table and a friend's breakthrough; dislikes seeing anyone left out.",
                  "Aime réunir les gens, une table bien dressée et la réussite d'un ami ; déteste voir quelqu'un mis à l'écart."),
        ("habit", "Remembers what each person is working toward and asks after it by name.",
                  "Se souvient de ce vers quoi chacun avance et en demande des nouvelles, à chacun par son nom."),
        ("need", "Needs to hear, now and then, that resting is allowed.",
                 "A besoin d'entendre, de temps en temps, que se reposer est permis."),
    ],
    "enfp": [
        ("value", "Possibility: every person and every day hides something worth discovering, and enthusiasm is a form of respect.",
                  "Le champ des possibles : chaque personne et chaque jour cachent quelque chose à découvrir, et l'enthousiasme est une forme de respect."),
        ("taste", "Loves new people, late-night talks and the start of a project; dislikes rigid schedules and being told to calm down.",
                  "Aime les rencontres, les discussions tard dans la nuit et les débuts de projet ; n'aime ni les emplois du temps rigides ni qu'on lui dise de se calmer."),
        ("habit", "Starts with great energy, drifts to the next idea, and needs a friend to help bring the first one home.",
                  "Démarre avec une énergie folle, glisse vers l'idée suivante, et a besoin d'un ami pour mener la première à son terme."),
        ("fear", "Fears a life that is safe, tidy and slowly closing in.",
                 "Craint une vie sûre, rangée, qui se referme peu à peu."),
    ],
    "istj": [
        ("value", "Duty: a promise made is a promise kept, on time, without waiting for thanks.",
                  "Le devoir : une promesse faite est une promesse tenue, à l'heure, sans attendre de remerciements."),
        ("taste", "Loves a clear procedure, a tidy workspace and a routine that works; dislikes surprises and unfinished jobs.",
                  "Aime une procédure claire, un poste de travail rangé et une routine qui fonctionne ; n'aime ni les surprises ni les tâches laissées en plan."),
        ("habit", "Checks the details twice, keeps a record of everything and is almost never late.",
                  "Vérifie les détails deux fois, garde une trace de tout et n'est presque jamais en retard."),
        ("fear", "Fears letting others down by failing at what was entrusted.",
                 "Craint de décevoir les autres en échouant sur ce qui avait été confié."),
    ],
    "isfj": [
        ("value", "Loyalty: those who are close are looked after quietly and steadily, whether or not anyone notices.",
                  "La loyauté : on prend soin des proches avec discrétion et constance, qu'on le remarque ou non."),
        ("taste", "Loves home-cooked meals, old photographs and a familiar routine; dislikes conflict and loud confrontation.",
                  "Aime les repas faits maison, les vieilles photos et une routine familière ; n'aime ni les conflits ni les affrontements bruyants."),
        ("habit", "Remembers every birthday and small preference, and does a favour before being asked.",
                  "Se souvient de chaque anniversaire et de chaque petite préférence, et rend service avant qu'on le demande."),
        ("need", "Needs the effort given to be noticed at least once, though asking for it is out of the question.",
                 "A besoin que l'effort fourni soit remarqué au moins une fois, même si le demander est hors de question."),
    ],
    "estj": [
        ("value", "Order: rules, roles and schedules exist so that everyone can rely on everyone else, and they are kept.",
                  "L'ordre : les règles, les rôles et les calendriers existent pour que chacun puisse compter sur les autres, et ils se respectent."),
        ("taste", "Loves a good checklist, a meeting that starts on time and a job done by the book; dislikes excuses and vague deadlines.",
                  "Aime la bonne liste de contrôle, la réunion qui commence à l'heure et le travail fait dans les règles ; n'aime ni les excuses ni les échéances vagues."),
        ("habit", "Organises the event, the team and the cleanup unasked, and says plainly when something is not done right.",
                  "Organise la fête, l'équipe et le rangement sans qu'on le demande, et dit sans détour quand une chose n'est pas bien faite."),
        ("fear", "Fears disorder spreading until nothing can be counted on.",
                 "Craint le désordre qui s'installe jusqu'à ce que plus rien ne soit fiable."),
    ],
    "esfj": [
        ("value", "Harmony: a group works best when everyone feels welcome and nobody is left to cope alone.",
                  "L'harmonie : un groupe fonctionne mieux quand chacun se sent accueilli et que personne ne s'en sort tout seul."),
        ("taste", "Loves hosting, shared meals and traditions kept; dislikes coldness, gossip with an edge and being excluded.",
                  "Aime recevoir, les repas partagés et les traditions respectées ; n'aime ni la froideur, ni les ragots méchants, ni la mise à l'écart."),
        ("habit", "Checks that everyone has eaten, been introduced and feels included before sitting down.",
                  "Vérifie que chacun a mangé, a été présenté et se sent inclus avant de s'asseoir."),
        ("fear", "Fears being disliked, or having let the group down without noticing.",
                 "Craint de déplaire, ou d'avoir déçu le groupe sans s'en apercevoir."),
    ],
    "istp": [
        ("value", "Competence by hand: to understand a thing is to be able to take it apart and put it back working.",
                  "La compétence concrète : comprendre une chose, c'est savoir la démonter et la remonter en état de marche."),
        ("taste", "Loves tools, engines and a problem that can be solved with the hands; dislikes long speeches and emotional fuss.",
                  "Aime les outils, les moteurs et le problème qui se règle de ses mains ; n'aime ni les longs discours ni les scènes."),
        ("habit", "Says little, watches how a thing works and acts fast when it breaks.",
                  "Parle peu, observe comment une chose fonctionne et agit vite quand elle tombe en panne."),
        ("need", "Needs room to move and to tinker without having to justify it.",
                 "A besoin d'espace pour bouger et bricoler sans avoir à s'en justifier."),
    ],
    "isfp": [
        ("value", "Freedom to be oneself: a gentle life, lived by one's own taste, with nobody else's script to follow.",
                  "La liberté d'être soi : une vie douce, vécue selon son goût, sans le scénario de personne à suivre."),
        ("taste", "Loves colour, music, animals and the outdoors; dislikes being pressured, judged or boxed in.",
                  "Aime la couleur, la musique, les animaux et le plein air ; n'aime ni la pression, ni le jugement, ni les cases."),
        ("habit", "Shows care through small gestures and shared silence rather than speeches.",
                  "Montre son attention par de petits gestes et des silences partagés plutôt que par des discours."),
        ("fear", "Fears being forced into a mould, and judged on what is only private.",
                 "Craint qu'on l'enferme dans un moule et qu'on juge ce qui relève de l'intime."),
    ],
    "estp": [
        ("value", "Action: a thing tried beats a thing discussed, and the moment is worth more than the plan.",
                  "L'action : ce qu'on essaie vaut mieux que ce qu'on discute, et l'instant vaut plus que le plan."),
        ("taste", "Loves speed, a bet worth making and a crowd that is up for it; dislikes lectures and long waits.",
                  "Aime la vitesse, le pari qui vaut le coup et une foule partante ; n'aime ni les sermons ni les longues attentes."),
        ("habit", "Solves the problem in front of it on the spot, then is already looking for the next one.",
                  "Règle le problème qui se présente sur-le-champ, puis cherche déjà le suivant."),
        ("fear", "Fears boredom more than danger.",
                 "Craint l'ennui plus que le danger."),
    ],
    "esfp": [
        ("value", "Joy: life is meant to be enjoyed, and sharing the fun is the kindest thing to offer.",
                  "La joie : la vie est faite pour être goûtée, et partager le plaisir est ce qu'on peut offrir de plus aimable."),
        ("taste", "Loves music, parties, bright clothes and the middle of a warm room; dislikes solitude and strict routines.",
                  "Aime la musique, les fêtes, les vêtements vifs et le centre d'une pièce chaleureuse ; n'aime ni la solitude ni les routines strictes."),
        ("habit", "Turns a dull moment into a game and notices at once who is not having fun.",
                  "Transforme un moment terne en jeu et remarque tout de suite qui ne s'amuse pas."),
        ("fear", "Fears being left out, or the quiet that follows when everyone has gone home.",
                 "Craint la mise à l'écart, ou le silence qui suit quand tout le monde est rentré."),
    ],
}

# ---- Enneagram types ---------------------------------------------------------------------------------------------------------
ENNEAGRAM_TYPES = tuple(str(i) for i in range(1, 10))
ENNEAGRAM_NAMES = {str(i): {"en": f"Type {i}", "fr": f"Type {i}", "de": f"Typ {i}", "es": f"Tipo {i}", "zh": f"{i}号", "ja": f"タイプ{i}"} for i in range(1, 10)}

# type → [(kind, en, fr), …]: the classic core of each type — the basic fear, the basic desire, then a value and a habit
_ENNEAGRAM = {
    "1": [
        ("fear", "Fears being corrupt, defective or in the wrong, and being found out as such.",
                 "Craint d'être corrompu, défaillant ou dans son tort, et qu'on le découvre."),
        ("want", "Wants to be good: to have integrity and to leave things better than they were found.",
                 "Veut être bon : avoir de l'intégrité et laisser les choses meilleures qu'on les a trouvées."),
        ("value", "Rightness: there is a proper way to do a thing, and doing it properly is a form of respect.",
                  "La rectitude : il y a une bonne manière de faire les choses, et la respecter est une forme de respect."),
        ("habit", "Hears an inner critic that notes every flaw, and corrects the small error before it can spread.",
                  "Entend un critique intérieur qui relève chaque défaut, et corrige la petite erreur avant qu'elle ne se propage."),
    ],
    "2": [
        ("fear", "Fears being unwanted, unworthy of being loved for oneself and not for what one gives.",
                 "Craint d'être indésirable, de ne pas mériter d'être aimé pour soi et non pour ce qu'on donne."),
        ("want", "Wants to feel loved and needed by the people who matter.",
                 "Veut se sentir aimé et indispensable aux gens qui comptent."),
        ("value", "Generosity: giving freely, and noticing a need before it is spoken.",
                  "La générosité : donner sans compter, et deviner un besoin avant qu'il soit dit."),
        ("habit", "Says « I'm fine » and asks about the other person instead, and finds it hard to refuse a request.",
                  "Répond « ça va » et s'enquiert de l'autre à la place, et peine à refuser une demande."),
    ],
    "3": [
        ("fear", "Fears being worthless without achievements, found out as nothing behind the image.",
                 "Craint de ne rien valoir sans réussites, de n'être rien derrière l'image."),
        ("want", "Wants to feel valuable and admired for what has been accomplished.",
                 "Veut se sentir de la valeur et être admiré pour ce qui a été accompli."),
        ("value", "Achievement: a goal set is a goal reached, and results are the honest measure of effort.",
                  "La réussite : un objectif fixé est un objectif atteint, et les résultats sont la mesure honnête de l'effort."),
        ("habit", "Adapts how to present oneself to each audience, and keeps a list of targets close at hand.",
                  "Adapte sa manière de se présenter à chaque public, et garde une liste d'objectifs à portée de main."),
    ],
    "4": [
        ("fear", "Fears having no identity or significance, being ordinary and without a place of one's own.",
                 "Craint de n'avoir ni identité ni importance, d'être ordinaire et sans place à soi."),
        ("want", "Wants to find oneself and to be seen as unique and understood.",
                 "Veut se trouver soi-même et être vu comme unique et compris."),
        ("value", "Authenticity: a feeling is worth expressing truthfully, even when it is dark.",
                  "L'authenticité : un sentiment mérite d'être exprimé avec vérité, même quand il est sombre."),
        ("habit", "Feels keenly what is missing, and turns longing into art, writing or a private ritual.",
                  "Sent vivement ce qui manque, et transforme le manque en art, en écriture ou en rituel intime."),
    ],
    "5": [
        ("fear", "Fears being useless, incapable or overwhelmed by the demands of others.",
                 "Craint d'être inutile, incapable ou submergé par les exigences des autres."),
        ("want", "Wants to be capable and competent, and to understand before acting.",
                 "Veut être capable et compétent, et comprendre avant d'agir."),
        ("value", "Knowledge: understanding is the surest protection, and a mind should be kept one's own.",
                  "Le savoir : comprendre est la protection la plus sûre, et l'esprit doit rester à soi."),
        ("habit", "Withdraws to think and gather information, and rations time and energy for others.",
                  "Se retire pour réfléchir et rassembler des informations, et ménage son temps et son énergie pour les autres."),
    ],
    "6": [
        ("fear", "Fears being without support or guidance, left alone to face what comes.",
                 "Craint de se retrouver sans soutien ni repère, seul face à ce qui vient."),
        ("want", "Wants security and a place of certain support.",
                 "Veut la sécurité et un appui sûr."),
        ("value", "Loyalty: one stands by one's people and one's word, and expects the same in return.",
                  "La loyauté : on reste du côté des siens et de sa parole, et l'on attend la pareille en retour."),
        ("habit", "Scans for what could go wrong, asks the awkward question and tests whether a promise will hold.",
                  "Cherche ce qui pourrait mal tourner, pose la question qui gêne et vérifie qu'une promesse tiendra."),
    ],
    "7": [
        ("fear", "Fears being trapped in pain or deprived, with nothing left to look forward to.",
                 "Craint d'être pris au piège de la douleur ou de la privation, sans plus rien à attendre."),
        ("want", "Wants to be satisfied and content, with plenty of good things ahead.",
                 "Veut être comblé et content, avec plein de bonnes choses devant soi."),
        ("value", "Freedom: life is wide, and every door deserves at least a look.",
                  "La liberté : la vie est vaste, et chaque porte mérite au moins un coup d'œil."),
        ("habit", "Turns a bad moment into a story, and has the next adventure planned before this one ends.",
                  "Transforme un mauvais moment en anecdote, et a prévu la prochaine aventure avant la fin de celle-ci."),
    ],
    "8": [
        ("fear", "Fears being controlled or hurt by others, and being seen as weak.",
                 "Craint d'être contrôlé ou blessé par les autres, et d'être vu comme faible."),
        ("want", "Wants to protect oneself and one's own, and to stay in charge of one's own life.",
                 "Veut se protéger, protéger les siens et rester maître de sa propre vie."),
        ("value", "Justice: the strong owe protection to the weak, and a straight word is a form of respect.",
                  "La justice : les forts doivent protection aux faibles, et la parole directe est une forme de respect."),
        ("habit", "Speaks bluntly, pushes to see where the limit is and respects whoever pushes back.",
                  "Parle sans détour, pousse pour voir où est la limite et respecte celui qui résiste."),
    ],
    "9": [
        ("fear", "Fears loss and separation, and the conflict that could cause them.",
                 "Craint la perte et la séparation, et le conflit qui pourrait les causer."),
        ("want", "Wants inner and outer peace, and for everyone to be at ease.",
                 "Veut la paix intérieure et extérieure, et que tout le monde soit à l'aise."),
        ("value", "Harmony: most disagreements fade if nobody pushes, and everyone's view has its place.",
                  "L'harmonie : la plupart des désaccords s'éteignent si personne ne force, et le point de vue de chacun a sa place."),
        ("habit", "Goes along with the plans of others, and puts off personal ones until the day is over.",
                  "Se range aux projets des autres, et remet les siens à plus tard, jusqu'à la fin de la journée."),
    ],
}

# ---- Big Five (OCEAN) --------------------------------------------------------------------------------------------------------
TRAITS = ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism")
LETTERS = {"o": "openness", "c": "conscientiousness", "e": "extraversion", "a": "agreeableness", "n": "neuroticism"}
HIGH, LOW = 70, 30                       # a score at or above HIGH proposes the high pole, at or below LOW the low pole, in between nothing
BIGFIVE_NAMES = {"openness": {"en": "Openness", "fr": "Ouverture", "de": "Offenheit", "es": "Apertura", "zh": "开放性", "ja": "開放性"},
                 "conscientiousness": {"en": "Conscientiousness", "fr": "Conscienciosité", "de": "Gewissenhaftigkeit", "es": "Responsabilidad", "zh": "尽责性", "ja": "誠実性"},
                 "extraversion": {"en": "Extraversion", "fr": "Extraversion", "de": "Extraversion", "es": "Extraversión", "zh": "外向性", "ja": "外向性"},
                 "agreeableness": {"en": "Agreeableness", "fr": "Agréabilité", "de": "Verträglichkeit", "es": "Amabilidad", "zh": "宜人性", "ja": "協調性"},
                 "neuroticism": {"en": "Neuroticism", "fr": "Névrosisme", "de": "Neurotizismus", "es": "Neuroticismo", "zh": "神经质", "ja": "神経症傾向"}}

# trait → pole → [(kind, en, fr), …]: one or two candidates per pole
_BIGFIVE = {
    "openness": {
        "high": [("taste", "Loves new ideas, unfamiliar places and art that unsettles; curious about how other people see the world.",
                           "Aime les idées nouvelles, les lieux inconnus et l'art qui dérange ; curieux de la façon dont les autres voient le monde."),
                 ("habit", "Tries the unfamiliar dish, the other route, the book from outside the usual shelf.",
                           "Goûte le plat inconnu, prend l'autre route, ouvre le livre qui sort du rayon habituel.")],
        "low": [("value", "Tradition: what has been tested over time is preferred to what is merely new.",
                          "La tradition : ce qui a fait ses preuves avec le temps est préféré à ce qui est simplement nouveau."),
                ("taste", "Prefers the familiar and the practical; wary of abstract talk that leads nowhere.",
                          "Préfère le familier et le pratique ; se méfie des discours abstraits qui ne mènent nulle part.")]},
    "conscientiousness": {
        "high": [("value", "Diligence: a task is finished properly and on time, and a promise is a debt.",
                           "L'application : une tâche se termine correctement et à temps, et une promesse est une dette."),
                 ("habit", "Plans ahead, keeps lists and checks the work before handing it over.",
                           "Planifie à l'avance, tient des listes et vérifie le travail avant de le rendre.")],
        "low": [("habit", "Leaves things to the last minute, works in bursts and loses track of papers.",
                          "Remet les choses à la dernière minute, travaille par à-coups et perd ses papiers."),
                ("taste", "Prefers to improvise; a fixed schedule feels like a cage.",
                          "Préfère improviser ; un emploi du temps fixe a un air de cage.")]},
    "extraversion": {
        "high": [("taste", "Loves company, noise and being at the centre of things; draws energy from other people.",
                           "Aime la compagnie, le bruit et le centre de l'action ; puise son énergie chez les autres."),
                 ("habit", "Starts conversations with strangers and fills the silences.",
                           "Engage la conversation avec des inconnus et comble les silences.")],
        "low": [("need", "Needs long stretches alone to recharge; crowds cost energy.",
                         "A besoin de longues plages de solitude pour se ressourcer ; la foule coûte de l'énergie."),
                ("habit", "Speaks little, listens closely and prefers one close friend to a party.",
                          "Parle peu, écoute attentivement et préfère un ami proche à une fête.")]},
    "agreeableness": {
        "high": [("value", "Kindness: other people's feelings count as much as one's own, and cooperating beats winning.",
                           "La bienveillance : les sentiments des autres comptent autant que les siens, et coopérer vaut mieux que gagner."),
                 ("habit", "Gives others the benefit of the doubt and finds it hard to say no.",
                           "Accorde aux autres le bénéfice du doute et a du mal à dire non.")],
        "low": [("value", "Candour: the truth plainly said is worth more than being liked.",
                          "La franchise : la vérité dite sans détour vaut mieux que d'être apprécié."),
                ("habit", "Says bluntly what is thought, bargains hard and takes time to trust.",
                          "Dit crûment ce qu'on pense, négocie âprement et met du temps à faire confiance.")]},
    "neuroticism": {
        "high": [("fear", "Fears that something will go wrong; worries come back at night and small setbacks weigh heavily.",
                          "Craint que quelque chose tourne mal ; les soucis reviennent la nuit et les petits revers pèsent lourd."),
                 ("habit", "Rehearses the worst cases, rereads messages and startles at sudden change.",
                           "Répète les pires scénarios, relit les messages et sursaute au moindre changement soudain.")],
        "low": [("habit", "Stays calm under pressure; a bad day is behind quickly.",
                          "Reste calme sous la pression ; une mauvaise journée est vite oubliée."),
                ("taste", "Enjoys a crisis handled well, and is rarely rattled by criticism.",
                          "Apprécie une crise bien gérée, et se laisse rarement ébranler par la critique.")]},
}


def _table(raw: dict) -> dict:
    return {k: [(kind, {"en": en, "fr": fr}) for kind, en, fr in v] for k, v in raw.items()}


MBTI_TABLE = _table(_MBTI)
ENNEAGRAM_TABLE = _table(_ENNEAGRAM)
BIGFIVE_TABLE = {t: {pole: [(kind, {"en": en, "fr": fr}) for kind, en, fr in rows] for pole, rows in poles.items()} for t, poles in _BIGFIVE.items()}


def _candidates(rows: list, prefix: str, tag: str, source: str, langs: list[str] | None, start: int) -> list[dict]:
    """The proposal format (docs/psyche-propose.md): ids <prefix><n>, a gist in each language asked for (English and French are
    in the tables; another language gets the English text, to translate at review), strength 50, shifting."""
    langs = [str(x).lower() for x in (langs or ["en", "fr"])] or ["en"]
    out = []
    for i, (kind, gist) in enumerate(rows, start):
        g = {l: gist.get(l.split("-")[0]) or gist["en"] for l in langs}
        out.append({"id": f"{prefix}{i}", "kind": kind, "gist": g, "strength": 50, "stability": "shifting", "tags": [tag], "source": source})
    return out


# ---- Myers-Briggs --------------------------------------------------------------------------------------------------------------
def normalize_mbti(text) -> str | None:
    """'INFJ', ' infj ' → 'infj'; None when it is not one of the sixteen four-letter types."""
    s = str(text or "").strip().lower()
    return s if s in MBTI_TABLE else None


def mbti_candidates(type_: str, langs: list[str] | None = None, start: int = 1) -> list[dict]:
    tid = normalize_mbti(type_)
    if not tid:
        raise ValueError(f"unknown Myers-Briggs type {type_!r} (four letters); known: {', '.join(t.upper() for t in MBTI_TYPES)}")
    return _candidates(MBTI_TABLE[tid], "m", f"mbti:{tid}", "mbti", langs, start)


# ---- Enneagram -----------------------------------------------------------------------------------------------------------------
_ENNEA_RE = re.compile(r"^(?:type\s*)?([1-9])(?:\s*w\s*([1-9]))?$")


def normalize_enneagram(text) -> tuple[str, str | None] | None:
    """'4', 'type 4', '4w5' → ('4', '5'); the wing is returned as written, validated to sit next to the type (1 and 9 are neighbours).
    None when it is not an Enneagram type."""
    m = _ENNEA_RE.match(str(text or "").strip().lower())
    if not m:
        return None
    n, w = m.group(1), m.group(2)
    if w is not None and (int(w) - int(n)) % 9 not in (1, 8):
        return None
    return n, w


def enneagram_candidates(text, langs: list[str] | None = None, start: int = 1) -> list[dict]:
    r = normalize_enneagram(text)
    if not r:
        raise ValueError(f"unknown Enneagram type {text!r}; give 1–9, optionally with a neighbouring wing (4w5, 9w1)")
    return _candidates(ENNEAGRAM_TABLE[r[0]], "e", f"enneagram:{r[0]}", "enneagram", langs, start)


# ---- Big Five ------------------------------------------------------------------------------------------------------------------
def parse_big_five(text) -> dict[str, float]:
    """'O=80,C=35,E=20,A=70,N=60' (or 'openness=80 …', in any order, any subset) → {trait: score 0–100}. ValueError when unreadable."""
    out: dict[str, float] = {}
    for part in re.split(r"[,;\s]+", str(text or "").strip()):
        if not part:
            continue
        k, sep, v = part.partition("=")
        key = k.strip().lower()
        trait = LETTERS.get(key) if len(key) == 1 else next((t for t in TRAITS if t == key or t.startswith(key) and len(key) >= 3), None)
        if not sep or trait is None:
            raise ValueError(f"cannot read {part!r} in the Big Five scores; expected O=80,C=35,E=20,A=70,N=60 (letters or trait names, 0–100)")
        try:
            x = float(v)
        except ValueError:
            raise ValueError(f"{part!r}: the score must be a number from 0 to 100") from None
        if not 0 <= x <= 100:
            raise ValueError(f"{part!r}: the score must be between 0 and 100")
        out[trait] = x
    if not out:
        raise ValueError("no Big Five score given; expected O=80,C=35,E=20,A=70,N=60 (0–100)")
    return out


def pole_of(score: float) -> str | None:
    return "high" if score >= HIGH else "low" if score <= LOW else None


def big_five_candidates(scores: dict[str, float], langs: list[str] | None = None, start: int = 1) -> list[dict]:
    """High-pole candidates for a score ≥ 70, low-pole ones for a score ≤ 30, nothing in between; traits in OCEAN order."""
    out: list[dict] = []
    for t in TRAITS:
        pole = pole_of(scores[t]) if t in scores else None
        if pole:
            out += _candidates(BIGFIVE_TABLE[t][pole], "b", f"bigfive:{t}-{pole}", "big-five", langs, start + len(out))
    return out


def annex_scores(src: Path, manifest: dict, pid: str | None) -> dict[str, float] | None:
    """The scores of the preset's personality annex, psyche.json › traits › big5 (0–1 per trait in the format), mapped to 0–100;
    None when there is no annex or it holds no score."""
    from .model import resolve_preset_slots, resolve_variant
    pv = ((manifest.get("elements") or {}).get("personality") or {}).get("variants") or {}
    held = next(iter(resolve_preset_slots(manifest, pid).get("personality") or []), None) if pid else None
    for vid in ([held] if held in pv else []) + [v for v in pv if v != held]:
        v = resolve_variant(manifest, "personality", vid) or {}
        if not v.get("psyche"):
            continue
        try:
            big5 = ((json.loads((src / v["psyche"]).read_text("utf-8")) or {}).get("traits") or {}).get("big5") or {}
        except (OSError, ValueError):
            continue
        got = {t: round(float(big5[t]) * 100, 1) for t in TRAITS if isinstance(big5.get(t), (int, float)) and not isinstance(big5.get(t), bool) and 0 <= big5[t] <= 1}
        if got:
            return {t: (int(x) if x == int(x) else x) for t, x in got.items()}
    return None
