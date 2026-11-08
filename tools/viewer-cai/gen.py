#!/usr/bin/env python3
"""Generate viewer/character-ai/index.html — the explorer for people coming from Character.AI — from viewer/index.html.

The base explorer is never edited for it: this script copies it and applies a few patches (a title, the samples one
folder up, a file opens on its memories graph, a welcome window in six languages). Every patch must match exactly once:
when the explorer changes so that one no longer applies, the script fails loudly instead of writing a wrong page.
Run it after every change to viewer/index.html:  python tools/viewer-cai/gen.py   (--check: fail if out of date)."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC, OUT = ROOT / "viewer" / "index.html", ROOT / "viewer" / "character-ai" / "index.html"

WELCOME = {  # title, open the file, the graph, the rest of COF, open button, close button, header link, example button, « see an example »
    "en": ["Welcome — your Character.AI conversations",
           "Open the .cof file the import page gave you (“Open a .cof”, or drop it here). It never leaves your browser.",
           "You land on the graph of its memories: the period “Conversations on Character.AI”, and each conversation is a memory linked to it. Click one, then “+” to read it whole.",
           "The other tabs show what a COF character can hold: looks, a voice, presets, a psyche. The builder adds them.",
           "Open my .cof", "Close", "Character.AI version", "Example: Wren", "See an example"],
    "fr": ["Bienvenue — vos conversations Character.AI",
           "Ouvrez le fichier .cof que la page d'import vous a donné (« Ouvrir un .cof », ou glissez-le ici). Il ne quitte jamais votre navigateur.",
           "Vous arrivez sur le graphe de ses souvenirs : la période « Conversations sur Character.AI », et chaque conversation est un souvenir relié à elle. Cliquez-en un, puis « + » pour la lire en entier.",
           "Les autres onglets montrent ce qu'un personnage COF peut porter : apparences, voix, presets, psyché. Le builder les ajoute.",
           "Ouvrir mon .cof", "Fermer", "version Character.AI", "Exemple : Wren", "Voir un exemple"],
    "de": ["Willkommen — Ihre Character.AI-Gespräche",
           "Öffnen Sie die .cof-Datei, die Ihnen die Importseite gegeben hat („.cof öffnen“ oder hierher ziehen). Sie verlässt Ihren Browser nie.",
           "Sie landen im Graphen ihrer Erinnerungen: der Zeitraum „Gespräche auf Character.AI“, und jedes Gespräch ist eine damit verbundene Erinnerung. Klicken Sie eine an, dann „+“, um sie ganz zu lesen.",
           "Die anderen Reiter zeigen, was eine COF-Figur enthalten kann: Aussehen, eine Stimme, Presets, eine Psyche. Der Builder fügt sie hinzu.",
           "Meine .cof öffnen", "Schließen", "Character.AI-Version", "Beispiel: Wren", "Ein Beispiel ansehen"],
    "es": ["Bienvenido — sus conversaciones de Character.AI",
           "Abra el archivo .cof que le dio la página de importación («Abrir un .cof», o arrástrelo aquí). Nunca sale de su navegador.",
           "Llega al grafo de sus recuerdos: el período «Conversaciones en Character.AI», y cada conversación es un recuerdo unido a él. Haga clic en uno y luego en «+» para leerla entera.",
           "Las otras pestañas muestran lo que puede llevar un personaje COF: apariencias, una voz, presets, una psique. El builder las añade.",
           "Abrir mi .cof", "Cerrar", "versión Character.AI", "Ejemplo: Wren", "Ver un ejemplo"],
    "zh": ["欢迎——您的 Character.AI 对话",
           "打开导入页面给您的 .cof 文件（“打开 .cof”，或拖放到这里）。它永远不会离开您的浏览器。",
           "您会看到它的记忆图：“在 Character.AI 上的对话”这一时期，每段对话都是与之相连的一段记忆。点击其中一段，再点“+”即可完整阅读。",
           "其他标签页展示了 COF 角色可以包含的内容：外观、声音、预设、心理。可以在 builder 中添加。",
           "打开我的 .cof", "关闭", "Character.AI 版", "示例：Wren", "查看示例"],
    "ja": ["ようこそ — Character.AI の会話",
           "取り込みページで作った .cof ファイルを開いてください（「.cof を開く」またはここにドロップ）。ファイルがブラウザの外に出ることはありません。",
           "記憶のグラフが表示されます：「Character.AI での会話」という期間があり、各会話はそれにつながる記憶です。1 つをクリックし、「+」で全文を読めます。",
           "ほかのタブは COF キャラクターが持てるものを示します：外見、声、プリセット、心理。builder で追加できます。",
           "自分の .cof を開く", "閉じる", "Character.AI 版", "例：Wren", "例を見る"],
}

OG = ("\n<meta property=\"og:type\" content=\"website\">"
      "\n<meta property=\"og:title\" content=\"COF Explorer — Character.AI version\">"
      "\n<meta property=\"og:description\" content=\"Read your Character.AI conversations again, as the memories of your character, in one open file. Nothing leaves your browser.\">"
      "\n<meta property=\"og:url\" content=\"https://yannsouetre.github.io/cof/viewer/character-ai/\">"
      "\n<meta property=\"og:image\" content=\"https://yannsouetre.github.io/cof/import/og-import.jpg\">"
      "\n<meta property=\"og:image:width\" content=\"1200\">\n<meta property=\"og:image:height\" content=\"630\">"
      "\n<meta name=\"twitter:card\" content=\"summary_large_image\">"
      "\n<meta name=\"twitter:image\" content=\"https://yannsouetre.github.io/cof/import/og-import.jpg\">")

CSS = ("#caiW{position:fixed;inset:0;background:rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;z-index:100;padding:16px}"
       "#caiW[hidden]{display:none}#caiW .box{background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:14px;max-width:560px;width:100%;"
       "padding:22px 22px 18px;box-shadow:0 12px 40px rgba(0,0,0,.3)}#caiW h2{margin:0 0 10px;font-size:1.2rem}#caiW ol{margin:0 0 14px;padding-left:20px}"
       "#caiW li{margin:6px 0;line-height:1.5}#caiW .row{display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap}"
       "#caiW .primary{background:var(--accent);color:#fff;border-color:var(--accent)}#caiHelp{background:none;border:0;padding:0;color:var(--accent);"
       "text-decoration:underline;cursor:pointer;font:inherit}")

HTML = ('<div id="caiW" hidden role="dialog" aria-modal="true" aria-labelledby="caiWt"><div class="box"><h2 id="caiWt"></h2><ol><li data-cw="1"></li>'
        '<li data-cw="2"></li><li data-cw="3"></li></ol><div class="row"><button id="caiWx"></button><button id="caiWe"></button><button class="primary" id="caiWo"></button></div></div></div>')

JS = """<script>/* Character.AI version (tools/viewer-cai/gen.py): a welcome window in the explorer's language, shown at every visit (Yann, 8 Nov.) */
(function(){const W=%s;const box=document.getElementById("caiW");
  function fill(){const w=W[typeof LANG==="string"&&W[LANG]?LANG:"en"];document.getElementById("caiWt").textContent=w[0];for(const i of [1,2,3])box.querySelector('[data-cw="'+i+'"]').textContent=w[i];
    document.getElementById("caiWo").textContent=w[4];document.getElementById("caiWx").textContent=w[5];document.getElementById("caiHelp").textContent=w[6];document.getElementById("btnWren").textContent=w[7];document.getElementById("caiWe").textContent=w[8]}
  function show(){fill();box.hidden=false;document.getElementById("caiWo").focus()}
  function hide(){box.hidden=true}
  document.getElementById("caiWx").onclick=hide;document.getElementById("caiWe").onclick=()=>{hide();sample("wren-calloway.cof")};document.getElementById("btnWren").onclick=()=>sample("wren-calloway.cof");document.getElementById("caiWo").onclick=()=>{hide();document.getElementById("file").click()};
  box.addEventListener("click",e=>{if(e.target===box)hide()});document.addEventListener("keydown",e=>{if(e.key==="Escape"&&!box.hidden)hide()});
  document.getElementById("caiHelp").onclick=e=>{e.preventDefault();show()};
  const al=window.applyLang;if(typeof al==="function"){window.applyLang=function(){const r=al.apply(this,arguments);fill();return r}}
  fill();if(!new URLSearchParams(location.search).has("embed"))show()})();
</script>
""" 


def patches(src: str) -> str:
    import json
    out = src

    def sub(pattern, repl, regex=False):
        nonlocal out
        n = len(re.findall(pattern, out)) if regex else out.count(pattern)
        if n != 1:
            raise SystemExit(f"tools/viewer-cai/gen.py: patch not applicable ({n} matches): {pattern[:80]!r} — update the script")
        out = re.sub(pattern, lambda m: m.expand(repl), out) if regex else out.replace(pattern, repl)

    sub("<title>COF Explorer</title>", "<title>COF Explorer · Character.AI</title>" + OG)
    sub(r'(<span id="ver">explorer [0-9.]+</span>)', r'\1 · <button id="caiHelp" type="button">Character.AI version</button>', regex=True)
    sub('fetch("samples/"+name)', 'fetch("../samples/"+name)')
    # an example of what an import gives: Wren, a character imported from a (made-up) Character.AI export, with four looks
    sub('<button id="btnClara" data-i="sample1">Example: Clara</button>', '<button id="btnWren">Example: Wren</button>\n  <button id="btnClara" data-i="sample1">Example: Clara</button>')
    # a file opens on its memories graph (on the look when it has none)
    sub("const Z0=Z;Z=await zipRead(buf);await openZ(Z0);",
        'const Z0=Z;Z=await zipRead(buf);await openZ(Z0,{tab:"memories",memView:"graph"});'
        'if(!(M&&M.elements&&M.elements.memories)){tab="look";await render()}'
        'else{const h=document.querySelector(".memhead");if(h)h.scrollIntoView({block:"start"})}')
    # the time strip counts a moment at its own date only: an imported conversation is undated, even inside the
    # Character.AI period (the base explorer places it at the period's start, which would read « 3 conversations in 2022 »)
    sub("const dm=allMom.map(dOf),", "const dm=allMom.map(v=>{const w=info[v].n.when||{};return w.date||w.age?dOf(v):null}),")
    sub("</style>\n</head>", CSS + "</style>\n</head>")
    sub("</body>", HTML + "\n" + (JS % json.dumps(WELCOME, ensure_ascii=False)) + "</body>")
    head = "<!-- GENERATED by tools/viewer-cai/gen.py from viewer/index.html — do not edit; edit the explorer, then run the script -->\n"
    return head + out


def main():
    out = patches(SRC.read_text("utf-8"))
    if "--check" in sys.argv:
        if not OUT.is_file() or OUT.read_text("utf-8") != out:
            raise SystemExit("viewer/character-ai/index.html is out of date: run python tools/viewer-cai/gen.py")
        print("viewer/character-ai/index.html is up to date")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(out, "utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(out.encode('utf-8')):,} bytes)")


if __name__ == "__main__":
    main()
