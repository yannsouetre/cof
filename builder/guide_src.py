# -*- coding: utf-8 -*-
# Source unique du guide de la version avancée du builder : fenêtre du builder (guide.js) et pages du dépôt (docs/builder-guide*.md).
# Chaque page = (titre, [blocs]) ; un bloc = ("p", texte) ou ("ul", [items]). <b>…</b> autorisé.
G = {}

G["fr"] = [
("La version avancée en bref", [
 ("p", "Six étapes, dans l'ordre de la colonne de gauche :"),
 ("ul", ["<b>1 · Personnage(s)</b> — qui c'est : nom, fictif ou réel, morphologie.",
         "<b>2 · Éléments</b> — tout ce qui le décrit : textes, photos, voix, LoRA, 3D, poses, mouvements, fichiers.",
         "<b>3 · Presets</b> — les combinaisons prêtes à l'emploi : un look, un âge, un style, une langue.",
         "<b>4 · Droits</b> — ce que les autres ont le droit d'en faire.",
         "<b>5 · Contrôles</b> — ce qui manque ou ne colle pas.",
         "<b>6 · Build</b> — le fichier .cof final."]),
 ("p", "Seuls le nom, fictif ou réel, la morphologie et les droits sont obligatoires. La version facile ne gère qu'un personnage simple (une fiche, des photos, une voix) : un fichier plus riche reste en version avancée."),
]),
("Catégories et déclinaisons", [
 ("p", "Les éléments sont rangés en 8 catégories : Personnalité, Apparence, Poids d'identité (LoRA), 3D, Voix, Postures, Mouvements, Fichiers. Dans chaque catégorie, vous ajoutez des <b>déclinaisons</b>, chacune d'un type : visage, corps, coiffure, vêtement, lieu…"),
 ("p", "<b>Règle d'or : une déclinaison = un ensemble cohérent d'une seule chose.</b> Plusieurs photos servent uniquement à montrer différents angles. Un autre visage, une autre coiffure, un autre vêtement, un autre lieu = une autre déclinaison."),
 ("ul", ["<b>Photos en vrac</b> : la seule exception, assumée. Visage, corps et tenue mélangés, mais toujours la même personne, au même âge, dans le même style.",
         "<b>Character sheet</b> : une planche qui montre le personnage entier (visage, corps, coiffure, tenue) sur une seule image."]),
]),
("L'âge", [
 ("ul", ["L'âge appartient à chaque <b>représentation</b> (visage, corps, planche, photos en vrac, LoRA, 3D), pas au personnage : Clara peut avoir un visage à 12 ans et un autre à 29 ans.",
         "Vêtements, accessoires, lieux et descriptions n'ont pas d'âge.",
         "Un preset prend l'âge le plus bas de ses déclinaisons.",
         "Une même image ne peut pas servir à la fois à un âge de moins de 18 ans et à un âge adulte."]),
]),
("Presets", [
 ("p", "Un preset = un personnage + une combinaison de déclinaisons. Par exemple : « Clara 29 ans, photo », « Clara manga », « Clara 65 ans »."),
 ("ul", ["<b>Un seul</b> visage, corps, coiffure par preset.",
         "<b>Se cumulent</b> : vêtements et accessoires (s'ils ne couvrent pas la même partie du corps), pilosité, particularités, lieux, plusieurs LoRA.",
         "<b>Proposé</b> = disponible dans ce preset, jamais appliqué d'office (une tenue de rechange, par exemple).",
         "Le <b>preset par défaut</b> s'ouvre en premier ; son visage de face devient la vignette du fichier."]),
]),
("Plusieurs personnages", [
 ("p", "Un fichier peut regrouper plusieurs personnages : un duo, une équipe. Chaque déclinaison et chaque preset appartient à un seul personnage, choisi dans le menu « Personnage » en haut de l'écran."),
 ("ul", ["Un visage, une voix ou un LoRA ne se partage jamais entre deux personnages.",
         "Un lieu, une pose ou un fichier neutre peut servir à plusieurs.",
         "Pour reprendre un preset d'un autre fichier : étape Presets, « Importer un preset (.cof) »."]),
]),
("Droits et contenus sensibles", [
 ("ul", ["Les droits sont <b>fermés par défaut</b> : vous ouvrez ce que vous autorisez (usage commercial, redistribution, clonage de voix, entraînement…), au besoin preset par preset.",
         "<b>Personne réelle</b> : le consentement est recommandé, et obligatoire pour la nudité ou le contenu intime.",
         "<b>Moins de 18 ans</b> : jamais de nudité ni de contenu intime dans le preset.",
         "Le contenu intime va uniquement dans sa déclinaison « intime », isolée et ignorée par défaut par les lecteurs."]),
]),
("Contrôles et build", [
 ("ul", ["<b>Contrôles</b> : la complétude (ce qui manque à chaque preset) et la cohérence (ce qui ne colle pas). Les avertissements ne bloquent jamais ; seules les erreurs empêchent le build.",
         "<b>Contrôle IA</b> (facultatif) : vous choisissez l'IA (adresse, clé, modèle). Elle vérifie que le preset décrit un seul personnage cohérent et que chaque déclinaison montre une seule chose. Les images partent vers cette IA ; la clé n'est pas enregistrée.",
         "<b>Build</b> : choisissez la taille et la compression des images, puis téléchargez le .cof. Ouvrez-le dans l'explorateur COF pour vérifier le résultat."]),
]),
]

G["en"] = [
("The advanced version in short", [
 ("p", "Six steps, in the order of the left column:"),
 ("ul", ["<b>1 · Character(s)</b> — who it is: name, fictional or real, morphology.",
         "<b>2 · Elements</b> — everything that describes it: texts, photos, voice, LoRA, 3D, poses, motion, files.",
         "<b>3 · Presets</b> — ready-to-use combinations: a look, an age, a style, a language.",
         "<b>4 · Rights</b> — what others may do with it.",
         "<b>5 · Checks</b> — what is missing or does not fit.",
         "<b>6 · Build</b> — the final .cof file."]),
 ("p", "Only the name, fictional or real, the morphology and the rights are required. The easy version handles only a simple character (one card, photos, one voice): a richer file stays in the advanced version."),
]),
("Categories and variants", [
 ("p", "Elements are sorted into 8 categories: Personality, Appearance, Identity weights (LoRA), 3D, Voice, Postures, Motion, Files. In each category you add <b>variants</b>, each of one type: face, body, hairstyle, garment, place…"),
 ("p", "<b>Golden rule: one variant = a consistent set of one thing.</b> Several photos only show different angles. Another face, another hairstyle, another garment, another place = another variant."),
 ("ul", ["<b>Loose photos</b>: the only exception, by design. Face, body and outfit mixed, but always the same person, at the same age, in the same style.",
         "<b>Character sheet</b>: one image showing the whole character (face, body, hairstyle, outfit)."]),
]),
("Age", [
 ("ul", ["Age belongs to each <b>representation</b> (face, body, sheet, loose photos, LoRA, 3D), not to the character: Clara can have a face at 12 and another at 29.",
         "Clothes, accessories, places and descriptions have no age.",
         "A preset takes the lowest age of its variants.",
         "One image can never serve both an age under 18 and an adult age."]),
]),
("Presets", [
 ("p", "A preset = one character + a combination of variants. For example: \"Clara 29, photo\", \"Clara manga\", \"Clara 65\"."),
 ("ul", ["<b>Only one</b> face, body, hairstyle per preset.",
         "<b>Stackable</b>: clothes and accessories (if they don't cover the same body part), facial and body hair, features, places, several LoRAs.",
         "<b>Offered</b> = available in this preset, never applied by default (a spare outfit, for example).",
         "The <b>default preset</b> opens first; its front face becomes the file's thumbnail."]),
]),
("Several characters", [
 ("p", "A file can group several characters: a duo, a team. Each variant and each preset belongs to one character, chosen in the \"Character\" menu at the top of the screen."),
 ("ul", ["A face, a voice or a LoRA is never shared between two characters.",
         "A neutral place, pose or file can serve several.",
         "To reuse a preset from another file: Presets step, \"Import a preset (.cof)\"."]),
]),
("Rights and sensitive content", [
 ("ul", ["Rights are <b>closed by default</b>: you open what you allow (commercial use, redistribution, voice cloning, training…), per preset if needed.",
         "<b>Real person</b>: consent is recommended, and required for nudity or intimate content.",
         "<b>Under 18</b>: never nudity or intimate content in the preset.",
         "Intimate content goes only in its \"intimate\" variant, kept apart and ignored by readers by default."]),
]),
("Checks and build", [
 ("ul", ["<b>Checks</b>: completeness (what each preset lacks) and coherence (what does not fit). Warnings never block; only errors prevent the build.",
         "<b>AI check</b> (optional): you choose the AI (address, key, model). It checks that the preset describes one consistent character and that each variant shows one thing. The images are sent to that AI; the key is not saved.",
         "<b>Build</b>: choose the image size and compression, then download the .cof. Open it in the COF explorer to check the result."]),
]),
]

G["de"] = [
("Die erweiterte Version kurz erklärt", [
 ("p", "Sechs Schritte, in der Reihenfolge der linken Spalte:"),
 ("ul", ["<b>1 · Figur(en)</b> — wer es ist: Name, fiktiv oder real, Morphologie.",
         "<b>2 · Elemente</b> — alles, was sie beschreibt: Texte, Fotos, Stimme, LoRA, 3D, Posen, Bewegungen, Dateien.",
         "<b>3 · Presets</b> — fertige Kombinationen: ein Look, ein Alter, ein Stil, eine Sprache.",
         "<b>4 · Rechte</b> — was andere damit tun dürfen.",
         "<b>5 · Prüfungen</b> — was fehlt oder nicht passt.",
         "<b>6 · Build</b> — die fertige .cof-Datei."]),
 ("p", "Pflicht sind nur Name, fiktiv oder real, Morphologie und Rechte. Die einfache Version kann nur eine einfache Figur (eine Karte, Fotos, eine Stimme): eine reichere Datei bleibt in der erweiterten Version."),
]),
("Kategorien und Varianten", [
 ("p", "Die Elemente sind in 8 Kategorien geordnet: Persönlichkeit, Aussehen, Identitätsgewichte (LoRA), 3D, Stimme, Posen, Bewegung, Dateien. In jeder Kategorie fügen Sie <b>Varianten</b> hinzu, jede mit einem Typ: Gesicht, Körper, Frisur, Kleidungsstück, Ort…"),
 ("p", "<b>Goldene Regel: eine Variante = ein stimmiges Set von genau einer Sache.</b> Mehrere Fotos zeigen nur verschiedene Blickwinkel. Ein anderes Gesicht, eine andere Frisur, ein anderes Kleidungsstück, ein anderer Ort = eine weitere Variante."),
 ("ul", ["<b>Lose Fotos</b>: die einzige Ausnahme, bewusst so. Gesicht, Körper und Outfit gemischt, aber immer dieselbe Person, im selben Alter, im selben Stil.",
         "<b>Character Sheet</b>: ein Bild, das die ganze Figur zeigt (Gesicht, Körper, Frisur, Outfit)."]),
]),
("Das Alter", [
 ("ul", ["Das Alter gehört zu jeder <b>Darstellung</b> (Gesicht, Körper, Sheet, lose Fotos, LoRA, 3D), nicht zur Figur: Clara kann ein Gesicht mit 12 und ein anderes mit 29 haben.",
         "Kleidung, Accessoires, Orte und Beschreibungen haben kein Alter.",
         "Ein Preset übernimmt das niedrigste Alter seiner Varianten.",
         "Ein Bild darf nie zugleich einem Alter unter 18 und einem Erwachsenenalter dienen."]),
]),
("Presets", [
 ("p", "Ein Preset = eine Figur + eine Kombination von Varianten. Zum Beispiel: „Clara 29, Foto“, „Clara Manga“, „Clara 65“."),
 ("ul", ["<b>Nur ein</b> Gesicht, Körper, eine Frisur pro Preset.",
         "<b>Kombinierbar</b>: Kleidung und Accessoires (wenn sie nicht dieselbe Körperpartie bedecken), Behaarung, Besonderheiten, Orte, mehrere LoRAs.",
         "<b>Angeboten</b> = in diesem Preset verfügbar, nie automatisch angewendet (z. B. ein Ersatz-Outfit).",
         "Das <b>Standard-Preset</b> öffnet sich zuerst; sein frontales Gesicht wird zum Vorschaubild der Datei."]),
]),
("Mehrere Figuren", [
 ("p", "Eine Datei kann mehrere Figuren bündeln: ein Duo, ein Team. Jede Variante und jedes Preset gehört zu genau einer Figur, gewählt im Menü „Figur“ oben auf dem Bildschirm."),
 ("ul", ["Ein Gesicht, eine Stimme oder ein LoRA wird nie zwischen zwei Figuren geteilt.",
         "Ein neutraler Ort, eine Pose oder eine Datei kann mehreren dienen.",
         "Ein Preset aus einer anderen Datei übernehmen: Schritt Presets, „Preset importieren (.cof)“."]),
]),
("Rechte und sensible Inhalte", [
 ("ul", ["Die Rechte sind <b>standardmäßig geschlossen</b>: Sie öffnen, was Sie erlauben (kommerzielle Nutzung, Weitergabe, Stimmklonen, Training…), bei Bedarf pro Preset.",
         "<b>Reale Person</b>: Einwilligung empfohlen, für Nacktheit oder intime Inhalte erforderlich.",
         "<b>Unter 18</b>: nie Nacktheit oder intime Inhalte im Preset.",
         "Intime Inhalte gehören nur in ihre Variante „intim“, getrennt gehalten und von Lesern standardmäßig ignoriert."]),
]),
("Prüfungen und Build", [
 ("ul", ["<b>Prüfungen</b>: Vollständigkeit (was jedem Preset fehlt) und Kohärenz (was nicht passt). Warnungen blockieren nie; nur Fehler verhindern den Build.",
         "<b>KI-Prüfung</b> (optional): Sie wählen die KI (Adresse, Schlüssel, Modell). Sie prüft, dass das Preset eine stimmige Figur beschreibt und jede Variante genau eine Sache zeigt. Die Bilder gehen an diese KI; der Schlüssel wird nicht gespeichert.",
         "<b>Build</b>: Bildgröße und Kompression wählen, dann die .cof herunterladen. Zur Kontrolle im COF-Explorer öffnen."]),
]),
]

G["es"] = [
("La versión avanzada en breve", [
 ("p", "Seis pasos, en el orden de la columna izquierda:"),
 ("ul", ["<b>1 · Personaje(s)</b> — quién es: nombre, ficticio o real, morfología.",
         "<b>2 · Elementos</b> — todo lo que lo describe: textos, fotos, voz, LoRA, 3D, poses, movimientos, archivos.",
         "<b>3 · Presets</b> — combinaciones listas para usar: un look, una edad, un estilo, un idioma.",
         "<b>4 · Derechos</b> — lo que otros pueden hacer con él.",
         "<b>5 · Controles</b> — lo que falta o no encaja.",
         "<b>6 · Build</b> — el archivo .cof final."]),
 ("p", "Solo son obligatorios el nombre, ficticio o real, la morfología y los derechos. La versión fácil solo gestiona un personaje sencillo (una ficha, fotos, una voz): un archivo más rico se queda en la versión avanzada."),
]),
("Categorías y variantes", [
 ("p", "Los elementos se ordenan en 8 categorías: Personalidad, Apariencia, Pesos de identidad (LoRA), 3D, Voz, Posturas, Movimientos, Archivos. En cada categoría añade <b>variantes</b>, cada una de un tipo: rostro, cuerpo, peinado, prenda, lugar…"),
 ("p", "<b>Regla de oro: una variante = un conjunto coherente de una sola cosa.</b> Varias fotos solo muestran distintos ángulos. Otro rostro, otro peinado, otra prenda, otro lugar = otra variante."),
 ("ul", ["<b>Fotos sueltas</b>: la única excepción, asumida. Rostro, cuerpo y atuendo mezclados, pero siempre la misma persona, a la misma edad, con el mismo estilo.",
         "<b>Hoja de personaje</b>: una imagen que muestra al personaje completo (rostro, cuerpo, peinado, atuendo)."]),
]),
("La edad", [
 ("ul", ["La edad pertenece a cada <b>representación</b> (rostro, cuerpo, hoja, fotos sueltas, LoRA, 3D), no al personaje: Clara puede tener un rostro a los 12 años y otro a los 29.",
         "La ropa, los accesorios, los lugares y las descripciones no tienen edad.",
         "Un preset toma la edad más baja de sus variantes.",
         "Una misma imagen nunca puede servir a la vez para una edad menor de 18 y una edad adulta."]),
]),
("Presets", [
 ("p", "Un preset = un personaje + una combinación de variantes. Por ejemplo: «Clara 29, foto», «Clara manga», «Clara 65»."),
 ("ul", ["<b>Un solo</b> rostro, cuerpo, peinado por preset.",
         "<b>Acumulables</b>: ropa y accesorios (si no cubren la misma parte del cuerpo), vello, particularidades, lugares, varios LoRA.",
         "<b>Propuesto</b> = disponible en este preset, nunca aplicado de entrada (un atuendo de recambio, por ejemplo).",
         "El <b>preset por defecto</b> se abre primero; su rostro de frente se convierte en la miniatura del archivo."]),
]),
("Varios personajes", [
 ("p", "Un archivo puede agrupar varios personajes: un dúo, un equipo. Cada variante y cada preset pertenece a un solo personaje, elegido en el menú «Personaje» arriba de la pantalla."),
 ("ul", ["Un rostro, una voz o un LoRA nunca se comparte entre dos personajes.",
         "Un lugar, una pose o un archivo neutro puede servir a varios.",
         "Para reutilizar un preset de otro archivo: paso Presets, «Importar un preset (.cof)»."]),
]),
("Derechos y contenidos sensibles", [
 ("ul", ["Los derechos están <b>cerrados por defecto</b>: usted abre lo que autoriza (uso comercial, redistribución, clonación de voz, entrenamiento…), preset por preset si hace falta.",
         "<b>Persona real</b>: el consentimiento es recomendable, y obligatorio para desnudez o contenido íntimo.",
         "<b>Menos de 18 años</b>: nunca desnudez ni contenido íntimo en el preset.",
         "El contenido íntimo va solo en su variante «íntima», aislada e ignorada por defecto por los lectores."]),
]),
("Controles y build", [
 ("ul", ["<b>Controles</b>: la completitud (lo que le falta a cada preset) y la coherencia (lo que no encaja). Los avisos nunca bloquean; solo los errores impiden el build.",
         "<b>Control por IA</b> (opcional): usted elige la IA (dirección, clave, modelo). Comprueba que el preset describe un solo personaje coherente y que cada variante muestra una sola cosa. Las imágenes se envían a esa IA; la clave no se guarda.",
         "<b>Build</b>: elija el tamaño y la compresión de las imágenes y descargue el .cof. Ábralo en el explorador COF para comprobar el resultado."]),
]),
]

G["zh"] = [
("高级版速览", [
 ("p", "六个步骤，按左侧栏的顺序："),
 ("ul", ["<b>1 · 角色</b>——是谁：名称、虚构或真实、形态。",
         "<b>2 · 元素</b>——描述角色的一切：文本、照片、声音、LoRA、3D、姿势、动作、文件。",
         "<b>3 · 预设</b>——现成的组合：一种造型、一个年龄、一种风格、一种语言。",
         "<b>4 · 权利</b>——他人可以怎样使用。",
         "<b>5 · 检查</b>——缺少什么、哪里不一致。",
         "<b>6 · 构建</b>——最终的 .cof 文件。"]),
 ("p", "只有名称、虚构或真实、形态和权利是必填的。简易版只处理简单角色（一张角色卡、照片、一个声音）：内容更丰富的文件留在高级版。"),
]),
("类别与变体", [
 ("p", "元素分为 8 个类别：性格、外观、身份权重（LoRA）、3D、声音、姿势、动作、文件。在每个类别中添加<b>变体</b>，每个变体有一个类型：脸、身体、发型、服装、地点……"),
 ("p", "<b>黄金法则：一个变体 = 一件事物的一致集合。</b>多张照片仅用于展示不同角度。另一张脸、另一种发型、另一件服装、另一个地点 = 另一个变体。"),
 ("ul", ["<b>散装照片</b>：唯一的例外，有意为之。脸、身体和服装混在一起，但始终是同一个人、同一年龄、同一风格。",
         "<b>角色设定图</b>：一张图展示完整角色（脸、身体、发型、服装）。"]),
]),
("年龄", [
 ("ul", ["年龄属于每个<b>表现形式</b>（脸、身体、角色设定图、散装照片、LoRA、3D），而不属于角色：Clara 可以有 12 岁的脸和 29 岁的脸。",
         "服装、配饰、地点和描述没有年龄。",
         "预设取其变体中最低的年龄。",
         "同一张图片绝不能同时用于未满 18 岁的年龄和成年年龄。"]),
]),
("预设", [
 ("p", "预设 = 一个角色 + 一组变体的组合。例如：“Clara 29 岁，照片”、“Clara 漫画风”、“Clara 65 岁”。"),
 ("ul", ["每个预设<b>只能有一个</b>脸、身体、发型。",
         "<b>可叠加</b>：服装和配饰（不覆盖同一身体部位时）、毛发、特征、地点、多个 LoRA。",
         "<b>可选</b> = 在该预设中可用，但从不默认应用（例如一套备用服装）。",
         "<b>默认预设</b>最先打开；其正面脸部成为文件的缩略图。"]),
]),
("多个角色", [
 ("p", "一个文件可以包含多个角色：二人组、团队。每个变体和每个预设只属于一个角色，在屏幕顶部的“角色”菜单中选择。"),
 ("ul", ["脸、声音或 LoRA 绝不在两个角色之间共享。",
         "中性的地点、姿势或文件可以供多个角色使用。",
         "要复用另一个文件中的预设：在“预设”步骤中，“导入预设（.cof）”。"]),
]),
("权利与敏感内容", [
 ("ul", ["权利<b>默认关闭</b>：由您开放所允许的用途（商业使用、再分发、声音克隆、训练……），必要时可按预设设置。",
         "<b>真实人物</b>：建议取得同意，裸露或私密内容则必须取得同意。",
         "<b>未满 18 岁</b>：预设中绝不能有裸露或私密内容。",
         "私密内容只能放在其“私密”变体中，单独存放，阅读器默认忽略。"]),
]),
("检查与构建", [
 ("ul", ["<b>检查</b>：完整度（每个预设缺少什么）和一致性（哪里不一致）。警告从不阻止；只有错误会阻止构建。",
         "<b>AI 检查</b>（可选）：由您选择 AI（地址、密钥、模型）。它检查预设是否描述了一个一致的角色，以及每个变体是否只展示一件事物。图片会发送给该 AI；密钥不会被保存。",
         "<b>构建</b>：选择图片尺寸和压缩方式，然后下载 .cof。在 COF 浏览器中打开以检查结果。"]),
]),
]

G["ja"] = [
("詳細版のあらまし", [
 ("p", "左の列の順に、6 つのステップがあります："),
 ("ul", ["<b>1 · キャラクター</b> — 誰か：名前、架空か実在か、形態。",
         "<b>2 · 要素</b> — キャラクターを表すすべて：テキスト、写真、声、LoRA、3D、ポーズ、モーション、ファイル。",
         "<b>3 · プリセット</b> — すぐ使える組み合わせ：見た目、年齢、スタイル、言語。",
         "<b>4 · 権利</b> — 他の人に許すこと。",
         "<b>5 · チェック</b> — 足りないもの、合わないもの。",
         "<b>6 · ビルド</b> — 完成した .cof ファイル。"]),
 ("p", "必須なのは名前、架空か実在か、形態、権利だけです。かんたん版はシンプルなキャラクター（カード 1 枚、写真、声 1 つ）だけを扱います。より豊かなファイルは詳細版のままです。"),
]),
("カテゴリーとバリアント", [
 ("p", "要素は 8 つのカテゴリーに分かれます：性格、外見、アイデンティティ重み（LoRA）、3D、声、ポーズ、モーション、ファイル。各カテゴリーに<b>バリアント</b>を追加し、それぞれに種類を指定します：顔、体、髪型、衣服、場所…"),
 ("p", "<b>大原則：1 つのバリアント = 1 つのものの一貫したセット。</b>複数の写真は角度違いを見せるためだけ。別の顔、別の髪型、別の衣服、別の場所 = 別のバリアント。"),
 ("ul", ["<b>未分類の写真</b>：唯一の例外（意図的）。顔・体・服装が混在してよいが、常に同じ人物・同じ年齢・同じスタイル。",
         "<b>キャラクターシート</b>：キャラクター全体（顔・体・髪型・服装）を 1 枚で見せる画像。"]),
]),
("年齢", [
 ("ul", ["年齢はキャラクターではなく、それぞれの<b>表現</b>（顔、体、シート、未分類の写真、LoRA、3D）に属します：Clara は 12 歳の顔と 29 歳の顔を持てます。",
         "衣服、アクセサリー、場所、説明には年齢がありません。",
         "プリセットはバリアントの中で最も低い年齢をとります。",
         "1 枚の画像を 18 歳未満の年齢と成人の年齢の両方に使うことはできません。"]),
]),
("プリセット", [
 ("p", "プリセット = 1 人のキャラクター + バリアントの組み合わせ。例：「Clara 29 歳、写真」「Clara マンガ」「Clara 65 歳」。"),
 ("ul", ["顔・体・髪型はプリセットごとに<b>1 つだけ</b>。",
         "<b>重ねられるもの</b>：衣服とアクセサリー（同じ部位を覆わない場合）、体毛、特徴、場所、複数の LoRA。",
         "<b>候補</b> = このプリセットで使えるが、既定では適用されない（替えの服など）。",
         "<b>既定のプリセット</b>が最初に開き、その正面の顔がファイルのサムネイルになります。"]),
]),
("複数のキャラクター", [
 ("p", "1 つのファイルに複数のキャラクター（コンビ、チーム）をまとめられます。各バリアントと各プリセットは 1 人のキャラクターに属し、画面上部の「キャラクター」メニューで選びます。"),
 ("ul", ["顔、声、LoRA は 2 人のキャラクターで共有できません。",
         "中立的な場所、ポーズ、ファイルは複数で使えます。",
         "別のファイルのプリセットを使うには：プリセットのステップで「プリセットを取り込む（.cof）」。"]),
]),
("権利とセンシティブな内容", [
 ("ul", ["権利は<b>既定で閉じています</b>：許可するもの（商用利用、再配布、声のクローン、学習…）を開きます。必要ならプリセットごとに。",
         "<b>実在の人物</b>：同意は推奨。ヌードやプライベートな内容では必須。",
         "<b>18 歳未満</b>：プリセットにヌードやプライベートな内容は一切不可。",
         "プライベートな内容は専用の「プライベート」バリアントにのみ入れ、分離され、リーダーは既定で無視します。"]),
]),
("チェックとビルド", [
 ("ul", ["<b>チェック</b>：完成度（各プリセットに足りないもの）と一貫性（合わないもの）。警告はブロックしません。ビルドを止めるのはエラーだけです。",
         "<b>AI チェック</b>（任意）：AI（アドレス、キー、モデル）を選びます。プリセットが一貫した 1 人のキャラクターを表しているか、各バリアントが 1 つのものだけを見せているかを確認します。画像はその AI に送られます。キーは保存されません。",
         "<b>ビルド</b>：画像のサイズと圧縮を選び、.cof をダウンロード。COF エクスプローラーで開いて結果を確認します。"]),
]),
]

UI = {  # fr, en, de, es, zh, ja
 "Guide": ("Guide","Guide","Leitfaden","Guía","指南","ガイド"),
 "Guide de la version avancée": ("Guide de la version avancée","Advanced version guide","Leitfaden der erweiterten Version","Guía de la versión avanzada","高级版指南","詳細版ガイド"),
 "Précédent": ("Précédent","Previous","Zurück","Anterior","上一页","前へ"),
 "Suivant": ("Suivant","Next","Weiter","Siguiente","下一页","次へ"),
 "Fermer": ("Fermer","Close","Schließen","Cerrar","关闭","閉じる"),
}
LANGS = ["fr","en","de","es","zh","ja"]
