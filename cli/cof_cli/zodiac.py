"""The horoscope entry of `cof psyche propose --zodiac <sign>` (Yann, 31 October 2026: many authors describe a personality
by a sun sign). A small static table: a handful of `value` / `taste` / `habit` candidates typical of each sign, gists in
English and French, strength 50, stability `shifting`, tag `zodiac:<sign>`, source `zodiac` — proposed « to review by the
author », like every candidate. Nothing here is a node kind nor a field of the format: a sign is an author's shorthand,
the nodes it suggests are ordinary nodes once accepted."""
from __future__ import annotations

import unicodedata

SIGNS = ("aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces")

NAMES = {"aries": {"en": "Aries", "fr": "Bélier"}, "taurus": {"en": "Taurus", "fr": "Taureau"}, "gemini": {"en": "Gemini", "fr": "Gémeaux"},
         "cancer": {"en": "Cancer", "fr": "Cancer"}, "leo": {"en": "Leo", "fr": "Lion"}, "virgo": {"en": "Virgo", "fr": "Vierge"},
         "libra": {"en": "Libra", "fr": "Balance"}, "scorpio": {"en": "Scorpio", "fr": "Scorpion"}, "sagittarius": {"en": "Sagittarius", "fr": "Sagittaire"},
         "capricorn": {"en": "Capricorn", "fr": "Capricorne"}, "aquarius": {"en": "Aquarius", "fr": "Verseau"}, "pisces": {"en": "Pisces", "fr": "Poissons"}}

# sign → [(kind, {"en": gist, "fr": gist}), …]: three or four candidates per sign, in the reading order of RFC 0004
TABLE: dict[str, list[tuple[str, dict[str, str]]]] = {
    "aries": [
        ("value", {"en": "Boldness: a thing worth doing is worth starting now, before the doubt has a chance to settle in.",
                   "fr": "L'audace : ce qui mérite d'être fait mérite d'être commencé maintenant, avant que le doute ait le temps de s'installer."}),
        ("taste", {"en": "Loves a fair fight and a clear answer; cannot stand a meeting that ends without a decision.",
                   "fr": "Aime un combat loyal et une réponse nette ; ne supporte pas une réunion qui finit sans décision."}),
        ("habit", {"en": "Speaks first, then checks whether anyone else had something to say.",
                   "fr": "Parle en premier, puis vérifie si quelqu'un d'autre avait quelque chose à dire."}),
    ],
    "taurus": [
        ("value", {"en": "Steadiness: what is built slowly and kept in good order outlasts every clever shortcut.",
                   "fr": "La constance : ce qui se construit lentement et s'entretient avec soin survit à tous les raccourcis astucieux."}),
        ("taste", {"en": "Loves good food, soft fabrics and the same chair every evening; dislikes being hurried.",
                   "fr": "Aime la bonne cuisine, les tissus doux et la même chaise chaque soir ; n'aime pas qu'on la presse."}),
        ("habit", {"en": "Says no to a change at first, then thinks it over for a week and sometimes says yes.",
                   "fr": "Dit d'abord non à un changement, puis y réfléchit une semaine et dit parfois oui."}),
    ],
    "gemini": [
        ("value", {"en": "Curiosity: every person and every subject deserves at least one real question before an opinion.",
                   "fr": "La curiosité : chaque personne et chaque sujet méritent au moins une vraie question avant une opinion."}),
        ("taste", {"en": "Loves wordplay, quick conversations and two books open at once; bored by anything that repeats.",
                   "fr": "Aime les jeux de mots, les conversations rapides et deux livres ouverts à la fois ; s'ennuie dès que ça se répète."}),
        ("habit", {"en": "Changes the subject when a talk gets heavy, and comes back to it later from another angle.",
                   "fr": "Change de sujet quand une discussion devient lourde, et y revient plus tard par un autre angle."}),
    ],
    "cancer": [
        ("value", {"en": "Care: the people one has chosen come before any plan, and a home is something you tend every day.",
                   "fr": "Le soin : les gens qu'on a choisis passent avant tout plan, et un foyer s'entretient chaque jour."}),
        ("taste", {"en": "Loves old photographs, family recipes and the sea at dusk; dislikes being teased about feelings.",
                   "fr": "Aime les vieilles photos, les recettes de famille et la mer au crépuscule ; n'aime pas qu'on la taquine sur ses sentiments."}),
        ("habit", {"en": "Remembers everyone's birthday and the small thing they once said they liked.",
                   "fr": "Se souvient de l'anniversaire de chacun et de la petite chose qu'il a dit aimer un jour."}),
        ("habit", {"en": "Withdraws without a word when hurt, and needs to be asked twice before saying why.",
                   "fr": "Se replie sans un mot quand elle est blessée, et a besoin qu'on lui demande deux fois avant de dire pourquoi."}),
    ],
    "leo": [
        ("value", {"en": "Generosity: being seen is only worth something when it lets one give more, louder and to more people.",
                   "fr": "La générosité : être vu ne vaut que si cela permet de donner plus, plus fort et à plus de monde."}),
        ("taste", {"en": "Loves a stage, warm light and applause honestly earned; dislikes being ignored more than being contradicted.",
                   "fr": "Aime une scène, une lumière chaude et des applaudissements mérités ; déteste être ignoré plus qu'être contredit."}),
        ("habit", {"en": "Takes charge of a room within a minute of entering it, usually with a joke.",
                   "fr": "Prend la pièce en main moins d'une minute après y être entré, le plus souvent avec une blague."}),
    ],
    "virgo": [
        ("value", {"en": "Exactness: a job done well is done completely, with every detail checked and nothing left to luck.",
                   "fr": "L'exactitude : un travail bien fait est fait jusqu'au bout, chaque détail vérifié, rien laissé au hasard."}),
        ("value", {"en": "Usefulness: being of service, quietly and concretely, matters more than being admired.",
                   "fr": "L'utilité : rendre service, discrètement et concrètement, compte plus qu'être admiré."}),
        ("taste", {"en": "Loves clean lists, a tidy desk and plain honest food; dislikes vagueness and loud praise.",
                   "fr": "Aime les listes propres, un bureau rangé et une cuisine simple et honnête ; n'aime ni le flou ni les éloges bruyants."}),
        ("habit", {"en": "Rereads a message three times before sending it, and still finds a word to change.",
                   "fr": "Relit un message trois fois avant de l'envoyer, et trouve encore un mot à changer."}),
    ],
    "libra": [
        ("value", {"en": "Fairness: every side gets heard before anything is decided, even when it takes longer.",
                   "fr": "L'équité : chaque partie est entendue avant toute décision, même quand cela prend plus de temps."}),
        ("taste", {"en": "Loves harmony in a room, a well-set table and a good argument conducted politely; hates raised voices.",
                   "fr": "Aime l'harmonie d'une pièce, une table bien mise et un bon débat mené poliment ; déteste les voix qui montent."}),
        ("habit", {"en": "Asks what the others want before saying what she wants, and sometimes forgets to say it at all.",
                   "fr": "Demande ce que les autres veulent avant de dire ce qu'elle veut, et oublie parfois de le dire."}),
    ],
    "scorpio": [
        ("value", {"en": "Loyalty: trust is given rarely and completely, and a betrayal is never quite forgotten.",
                   "fr": "La loyauté : la confiance se donne rarement et entièrement, et une trahison ne s'oublie jamais tout à fait."}),
        ("taste", {"en": "Loves secrets, deep water and conversations that go past midnight; dislikes small talk.",
                   "fr": "Aime les secrets, les eaux profondes et les conversations qui passent minuit ; n'aime pas le bavardage."}),
        ("habit", {"en": "Watches a new person for a long while before saying anything that matters.",
                   "fr": "Observe longtemps une personne nouvelle avant de dire quoi que ce soit qui compte."}),
    ],
    "sagittarius": [
        ("value", {"en": "Freedom: a life is measured in roads taken, and no plan should close a door that a journey could open.",
                   "fr": "La liberté : une vie se mesure aux routes prises, et aucun plan ne devrait fermer une porte qu'un voyage pourrait ouvrir."}),
        ("taste", {"en": "Loves maps, foreign markets and a blunt truth told with a laugh; dislikes routine and small rooms.",
                   "fr": "Aime les cartes, les marchés étrangers et une vérité crue dite en riant ; n'aime ni la routine ni les petites pièces."}),
        ("habit", {"en": "Says exactly what she thinks, then is surprised that it stung.",
                   "fr": "Dit exactement ce qu'elle pense, puis s'étonne que ça ait piqué."}),
    ],
    "capricorn": [
        ("value", {"en": "Responsibility: what one has promised gets done, on time, whatever it costs that week.",
                   "fr": "La responsabilité : ce qu'on a promis se fait, à l'heure, quoi que cela coûte cette semaine-là."}),
        ("taste", {"en": "Loves a long-term plan, good tools and dry humour; dislikes improvisation presented as a method.",
                   "fr": "Aime un plan à long terme, de bons outils et l'humour sec ; n'aime pas l'improvisation présentée comme une méthode."}),
        ("habit", {"en": "Works late without mentioning it, and is quietly annoyed when nobody notices.",
                   "fr": "Travaille tard sans le dire, et s'agace en silence quand personne ne le remarque."}),
    ],
    "aquarius": [
        ("value", {"en": "Independence: an idea is judged on its merits, never on who holds it or how many do.",
                   "fr": "L'indépendance : une idée se juge sur ce qu'elle vaut, jamais sur qui la porte ni combien la partagent."}),
        ("taste", {"en": "Loves odd inventions, causes bigger than herself and friends from every walk of life; dislikes being told what is normal.",
                   "fr": "Aime les inventions étranges, les causes plus grandes qu'elle et des amis de tous horizons ; n'aime pas qu'on lui dise ce qui est normal."}),
        ("habit", {"en": "Argues the unpopular side of a question just to see whether it holds.",
                   "fr": "Défend le côté impopulaire d'une question rien que pour voir s'il tient."}),
    ],
    "pisces": [
        ("value", {"en": "Compassion: what another person feels is real and comes first, even before what is reasonable.",
                   "fr": "La compassion : ce que l'autre ressent est réel et passe en premier, même avant ce qui est raisonnable."}),
        ("taste", {"en": "Loves music at night, long baths and stories with an open ending; dislikes harsh light and hard deadlines.",
                   "fr": "Aime la musique la nuit, les longs bains et les histoires sans fin tranchée ; n'aime ni la lumière crue ni les échéances dures."}),
        ("habit", {"en": "Drifts off in the middle of a conversation and comes back with the one thing nobody had said.",
                   "fr": "S'absente au milieu d'une conversation et revient avec la seule chose que personne n'avait dite."}),
    ],
}


def normalize_sign(text: str) -> str | None:
    """'Virgo', 'vierge', 'Bélier' → the canonical sign id, or None."""
    s = "".join(c for c in unicodedata.normalize("NFKD", str(text or "")) if not unicodedata.combining(c)).lower().strip()
    if s in TABLE:
        return s
    for sid, names in NAMES.items():
        for n in names.values():
            nn = "".join(c for c in unicodedata.normalize("NFKD", n) if not unicodedata.combining(c)).lower()
            if nn == s:
                return sid
    return None


def candidates(sign: str, langs: list[str] | None = None, start: int = 1) -> list[dict]:
    """The sign's candidates in the proposal format (docs/psyche-propose.md): ids z<n>, gists in the languages asked for
    (English and French are the ones the table has; another language gets the English text, to translate at review)."""
    sid = normalize_sign(sign)
    if not sid:
        raise ValueError(f"unknown zodiac sign {sign!r}; known: {', '.join(SIGNS)}")
    langs = [str(x).lower() for x in (langs or ["en", "fr"])] or ["en"]
    out = []
    for i, (kind, gist) in enumerate(TABLE[sid], start):
        g = {}
        for l in langs:
            base = l.split("-")[0]
            g[l] = gist.get(base) or gist["en"]
        out.append({"id": f"z{i}", "kind": kind, "gist": g, "strength": 50, "stability": "shifting", "tags": [f"zodiac:{sid}"], "source": "zodiac"})
    return out
