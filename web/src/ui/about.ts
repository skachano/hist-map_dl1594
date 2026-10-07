// About & sources: the book and its edition, what the map shows and how to read it, how the data
// was made, its author and terms, and the sources. Written out in each language.
import type { Dataset, Lang } from "../data/types";
import { t } from "../i18n";
import type { Store } from "../state/store";
import { compareSection, linkHistMap } from "./compare";
import { fill, h } from "./dom";

interface Section { title: string; paragraphs: string[] }

const TEXT: Record<Lang, Section[]> = {
  en: [
    { title: "The book", paragraphs: [
      "In 1594 Thierry Alix, president of the Chambre des Comptes of Lorraine and keeper of the ducal archives, drew up for Duke Charles III a description of the duchy: its bailliages, prévôtés, offices and lordships, and under each of them the towns, villages, castles and abbeys it contained, divided into the duke's domain, the fiefs and the church lands.",
      "The manuscript is lost. The text survives in copies, one of which the editors who sign \"H. L. et A. de B.\" published in 1870 in the Recueil de documents sur l'histoire de Lorraine. The editors numbered the 2,487 entries and added a table of old forms and a table of place names identifying each entry with a commune of 1870. This atlas is built from that edition, which is in the public domain.",
    ] },
    { title: "What the map shows", paragraphs: [
      "The map shows the duchy as Alix describes it in 1594. It has no time line: the book describes one moment.",
      "Two hierarchies are kept apart. Administrative divisions (bailiwicks, provostships, offices, castellanies, bans, mayoralties) tile the duchy. Feudal realms (counties, lordships, named fiefs, church lands) cover only their own places. Where a division and a realm cover the same land, both are recorded and linked: the panel says why.",
      "Tenure is what the book's sub-headings say: Domaine (the duke's), Fiedvez (fiefs), Clergé (church lands), and the villages under the duke's safeguard. Places held only in part (\"en partie\", \"pour la moitié\") are hatched.",
      "Areas are approximate. The book lists places, not boundaries: each located village gets the land nearer to it than to any other, up to 6 km, and a territory's area is the sum of its villages' land. Known foreign lands inside or along the duchy, where today's communes the book doesn't name keep their land out of it: Metz with the Pays messin, Toul, Verdun, the bishops' towns (Vic and Moyenvic, Rambervillers, Baccarat, Liverdun) and Saarbrücken. Elsewhere, the land between the book's villages is the duchy's. Land further off, such as the Barrois and the Empire, is left blank.",
      "The Settlements tab shows the tenures, or one of the book's thematic lists on the map: its towns, cathedrals and collegiate churches, abbeys, priories, convents and commanderies, or the chaumes, the summer pastures of the Vosges, which Alix gives by provostship and the map shades by their gîtes.",
    ] },
    { title: "How the data was made", paragraphs: [
      "The scan's OCR text was read page by page, the entry numbers recovered through the scan's misreadings, and the headings parsed into the two hierarchies. Each entry was matched to the editor's identification in the index by its number and its name, and the editor's corrections were applied. The two were then checked against each other number by number: every number the index prints leads to the entry it means (misread numbers were read again on the printed page), and an entry that names several places belongs to each of them. Each place keeps its spellings: the lists', the index's and the table of old forms'. Places were located with Wikidata and GeoNames near the commune or canton the index gives, and every location was checked against it. The topographical dictionaries of the Meurthe (Lepage), the Meuse (Liénard), the Moselle (Bouteiller) and the Vosges (Marichal) were then searched for each place's old spellings: they name hamlets the databases lack, and often quote this very text, Marichal by its entry numbers. Where they show the index's identification to be wrong, theirs is followed; the panel still shows what the index says. Hamlets with no point of their own sit at their commune and are drawn hollow.",
      "Nearly all the places the index identifies are located (99.9%), and nearly 99% of all the places the book names; most of the rest are fiefs and bans with no single site. Doubtful identifications and locations are marked in the panel, and every entry links to its page in the 1870 edition.",
      "Names the scan garbled were read again on the page images: the places' names, the index's headings, communes and cantons, and the entries' text, guided by a second OCR reading (Tesseract), DicoTopo's spellings of 1594 and the editors' table of old forms. For the German bailiwick, Henri Hiegel's identifications (Le bailliage d'Allemagne de 1600 à 1632, 1961, as recorded in the German Bailiwick atlas) settled places the index leaves open. The pipeline, the identifications and these readings were worked out with Claude (Anthropic) and reviewed by hand.",
      "German names are the places' historical German names where they have one (Bolchen for Boulay, Saargemünd for Sarreguemines). Japanese names are those of the German Bailiwick atlas where a place is in both atlases, else written in katakana as that atlas does: the French reading in France, the German one in Germany.",
    ] },
    { title: "Author", paragraphs: [
      "Conceived, curated and reviewed by Siargey Kachanovich. The atlas's data and texts are released under the Creative Commons Attribution 4.0 licence (CC BY 4.0): you may reuse and adapt them, with credit. Its code is under the MIT License. This does not cover the book and its 1870 edition, which are in the public domain, nor the base map and the sources below, which keep their own terms.",
    ] },
    { title: "Sources", paragraphs: [
      "Thierry Alix, Dénombrement du duché de Lorraine (1594), ed. H. L. et A. de B., Recueil de documents sur l'histoire de Lorraine, Nancy, 1870 (public domain).",
      "Base map © OpenStreetMap contributors (ODbL), via OpenFreeMap. Place data from Wikidata (CC0) and GeoNames (CC BY 4.0). Old place names from DicoTopo, the Dictionnaire topographique de la France (CTHS, École nationale des chartes and Archives nationales, dicotopo.cths.fr), under the Licence Ouverte 2.0, data of 5 October 2026.",
    ] },
  ],
  fr: [
    { title: "Le livre", paragraphs: [
      "En 1594, Thierry Alix, président de la Chambre des comptes de Lorraine et garde du Trésor des chartes, dressa pour le duc Charles III une description du duché : ses bailliages, prévôtés, offices et seigneuries, et sous chacun les villes, villages, châteaux et abbayes qu'il comprenait, répartis entre le domaine du duc, les fiefs et le clergé.",
      "Le manuscrit est perdu. Le texte subsiste dans des copies, dont l'une fut publiée en 1870, par les éditeurs qui signent « H. L. et A. de B. », dans le Recueil de documents sur l'histoire de Lorraine. Les éditeurs ont numéroté les 2 487 articles et ajouté une table des formes anciennes et une table des noms de lieux qui identifie chaque article avec une commune de 1870. Cet atlas repose sur cette édition, qui est dans le domaine public.",
    ] },
    { title: "Ce que montre la carte", paragraphs: [
      "La carte montre le duché tel qu'Alix le décrit en 1594. Elle n'a pas de frise chronologique : le livre décrit un moment.",
      "Deux hiérarchies sont distinguées. Les circonscriptions administratives (bailliages, prévôtés, offices, châtellenies, bans, mairies) couvrent tout le duché. Les seigneuries (comtés, terres et seigneuries, fiefs nommés, temporels d'Église) ne couvrent que leurs propres lieux. Quand une circonscription et une seigneurie couvrent le même territoire, les deux sont enregistrées et liées ; le panneau dit pourquoi.",
      "La tenure est celle que donnent les sous-titres du livre : Domaine (celui du duc), Fiedvez (fiefs), Clergé, et les villages sous la sauvegarde du duc. Les lieux tenus en partie (« en partie », « pour la moitié ») sont hachurés.",
      "Les surfaces sont approximatives. Le livre donne des lieux, pas des limites : chaque village localisé reçoit les terres plus proches de lui que de tout autre, jusqu'à 6 km, et la surface d'un territoire est la somme de celles de ses villages. Dans les terres étrangères connues, enclavées ou voisines, les communes actuelles que le livre ne nomme pas gardent leurs terres hors du duché : Metz et le Pays messin, Toul, Verdun, les villes des évêques (Vic et Moyenvic, Rambervillers, Baccarat, Liverdun) et Sarrebruck. Ailleurs, les terres entre les villages du livre sont au duché. Les terres plus lointaines, comme le Barrois ou l'Empire, restent en blanc.",
      "L'onglet Localités montre les tenures, ou l'une des listes thématiques du livre sur la carte : ses villes, cathédrales et collégiales, abbayes, prieurés, couvents et commanderies, ou les chaumes, pâturages d'été des Vosges, qu'Alix donne par prévôté et que la carte teinte selon leurs gîtes.",
    ] },
    { title: "Comment les données ont été faites", paragraphs: [
      "Le texte océrisé du scan a été lu page par page, les numéros des articles retrouvés malgré les erreurs de lecture, et les titres analysés en deux hiérarchies. Chaque article a été rapproché de l'identification de l'éditeur dans la table par son numéro et son nom, et les corrections de l'éditeur ont été appliquées. Les deux ont ensuite été vérifiés l'un par l'autre, numéro par numéro : chaque numéro de la table mène à l'article qu'il désigne (les numéros mal lus ont été relus sur la page imprimée), et un article qui nomme plusieurs lieux appartient à chacun. Chaque lieu garde ses graphies : celles des listes, de la table et de la table des formes anciennes. Les lieux ont été localisés avec Wikidata et GeoNames près de la commune ou du canton que donne la table, et chaque localisation a été vérifiée par rapport à eux. Les dictionnaires topographiques de la Meurthe (Lepage), de la Meuse (Liénard), de la Moselle (Bouteiller) et des Vosges (Marichal) ont ensuite été interrogés sur les formes anciennes de chaque lieu : ils nomment des écarts absents des bases et citent souvent ce texte même, Marichal par ses numéros d'articles. Quand ils montrent que l'identification de la table est fautive, la leur est suivie ; le panneau montre toujours ce que dit la table. Les écarts sans point propre sont placés sur leur commune et dessinés en creux.",
      "Presque tous les lieux identifiés par la table sont localisés (99,9 %), et près de 99 % de tous les lieux que nomme le livre ; la plupart des autres sont des fiefs et des bans sans emplacement unique. Les identifications et localisations douteuses sont signalées dans le panneau, et chaque article renvoie à sa page dans l'édition de 1870.",
      "Les noms que le scan a déformés ont été relus sur les images des pages : les noms des lieux, les entrées de la table, ses communes et cantons, et le texte des articles, guidés par une seconde lecture OCR (Tesseract), les graphies de 1594 de DicoTopo et la table des formes anciennes des éditeurs. Pour le bailliage d'Allemagne, les identifications d'Henri Hiegel (Le bailliage d'Allemagne de 1600 à 1632, 1961, telles que les reprend l'atlas du bailliage d'Allemagne) ont tranché pour des lieux que la table laisse ouverts. La chaîne de traitement, les identifications et ces relectures ont été élaborées avec Claude (Anthropic) et revues à la main.",
      "Les noms allemands sont les noms allemands historiques des lieux quand ils en ont un (Bolchen pour Boulay, Saargemünd pour Sarreguemines). Les noms japonais sont ceux de l'atlas du bailliage d'Allemagne quand un lieu figure dans les deux atlas, sinon transcrits en katakana comme il le fait : la lecture française en France, l'allemande en Allemagne.",
    ] },
    { title: "Auteur", paragraphs: [
      "Conçu, établi et vérifié par Siargey Kachanovich. Les données et les textes de l'atlas sont publiés sous la licence Creative Commons Attribution 4.0 (CC BY 4.0) : vous pouvez les réutiliser et les adapter en citant la source. Son code est sous licence MIT. Cela ne s'applique ni au livre ni à son édition de 1870, qui sont dans le domaine public, ni au fond de carte et aux sources ci-dessous, qui gardent leurs propres conditions.",
    ] },
    { title: "Sources", paragraphs: [
      "Thierry Alix, Dénombrement du duché de Lorraine (1594), éd. H. L. et A. de B., Recueil de documents sur l'histoire de Lorraine, Nancy, 1870 (domaine public).",
      "Fond de carte © contributeurs d'OpenStreetMap (ODbL), via OpenFreeMap. Données de lieux : Wikidata (CC0) et GeoNames (CC BY 4.0). Formes anciennes : DicoTopo, Dictionnaire topographique de la France (CTHS, École nationale des chartes et Archives nationales, dicotopo.cths.fr), sous Licence Ouverte 2.0, données du 5 octobre 2026.",
    ] },
  ],
  de: [
    { title: "Das Buch", paragraphs: [
      "1594 verfasste Thierry Alix, Präsident der lothringischen Rechenkammer und Hüter des herzoglichen Archivs, für Herzog Karl III. eine Beschreibung des Herzogtums: seine Ämter (bailliages), Propsteien, Kellereien und Herrschaften und darunter die Städte, Dörfer, Burgen und Abteien, geschieden in die Domäne des Herzogs, die Lehen und das Kirchengut.",
      "Die Handschrift ist verloren. Der Text ist in Abschriften erhalten, von denen die Herausgeber, die mit „H. L. et A. de B.“ zeichnen, 1870 eine im Recueil de documents sur l'histoire de Lorraine veröffentlichten. Die Herausgeber nummerierten die 2 487 Einträge und fügten eine Tabelle der alten Namensformen und ein Ortsregister hinzu, das jeden Eintrag einer Gemeinde von 1870 zuordnet. Der Atlas beruht auf dieser gemeinfreien Ausgabe.",
    ] },
    { title: "Was die Karte zeigt", paragraphs: [
      "Die Karte zeigt das Herzogtum, wie Alix es 1594 beschreibt. Sie hat keine Zeitleiste: das Buch beschreibt einen Zeitpunkt.",
      "Zwei Gliederungen werden getrennt. Die Verwaltungsbezirke (Bellistümer, Schultheißereien, Ämter, Kellereien, Banne, Meiereien) decken das ganze Herzogtum. Die Herrschaften (Grafschaften, Herrschaften, genannte Lehen, Kirchengut) decken nur ihre eigenen Orte. Wo ein Bezirk und eine Herrschaft dasselbe Gebiet umfassen, sind beide verzeichnet und verknüpft; das Seitenfeld sagt, warum.",
      "Die Besitzart folgt den Zwischentiteln des Buchs: Domaine (die des Herzogs), Fiedvez (Lehen), Clergé (Kirchengut) und die Dörfer unter herzoglichem Schirm. Nur teilweise gehaltene Orte („en partie“, „pour la moitié“) sind schraffiert.",
      "Flächen sind Näherungen. Das Buch nennt Orte, keine Grenzen: jedes verortete Dorf erhält das Land, das ihm näher liegt als jedem anderen, bis 6 km, und die Fläche eines Territoriums ist die Summe seiner Dörfer. In bekannten fremden Gebieten innerhalb oder am Rand des Herzogtums behalten heutige Gemeinden, die das Buch nicht nennt, ihr Land außerhalb: Metz mit dem Pays messin, Toul, Verdun, die Städte der Bischöfe (Vic und Moyenvic, Rambervillers, Baccarat, Liverdun) und Saarbrücken. Anderswo gehört das Land zwischen den Dörfern des Buches zum Herzogtum. Weiter entferntes Land wie das Barrois und das Reich bleibt weiß.",
      "Der Reiter Orte zeigt die Besitzarten oder eine der thematischen Listen des Buchs auf der Karte: seine Städte, Dome und Stiftskirchen, Abteien, Priorate, Konvente und Kommenden, oder die Hochweiden der Vogesen (chaumes), die Alix nach Schultheißereien aufführt und die Karte nach ihren gîtes tönt.",
    ] },
    { title: "Wie die Daten entstanden", paragraphs: [
      "Der OCR-Text des Scans wurde Seite für Seite gelesen, die Nummern der Einträge trotz Lesefehlern wiederhergestellt und die Überschriften in die zwei Gliederungen zerlegt. Jeder Eintrag wurde über Nummer und Namen mit der Bestimmung des Herausgebers im Register verbunden, und dessen Berichtigungen wurden angewandt. Beide wurden dann Nummer für Nummer gegeneinander geprüft: Jede Nummer des Registers führt zu dem Eintrag, den sie meint (falsch gelesene Nummern wurden auf der gedruckten Seite nachgelesen), und ein Eintrag, der mehrere Orte nennt, gehört zu jedem von ihnen. Jeder Ort behält seine Schreibweisen: die der Listen, des Registers und der Tabelle der alten Formen. Die Orte wurden mit Wikidata und GeoNames nahe der Gemeinde oder dem Kanton verortet, die das Register nennt, und jede Lage wurde daran geprüft. Danach wurden die topographischen Wörterbücher der Meurthe (Lepage), der Maas (Liénard), der Mosel (Bouteiller) und der Vogesen (Marichal) nach den alten Formen jedes Ortes durchsucht: Sie nennen Weiler, die in den Datenbanken fehlen, und zitieren oft eben diesen Text, Marichal mit den Nummern der Einträge. Wo sie zeigen, dass die Bestimmung des Registers falsch ist, wird ihre übernommen; das Seitenfeld zeigt weiterhin, was das Register sagt. Weiler ohne eigenen Punkt liegen bei ihrer Gemeinde und sind hohl gezeichnet.",
      "Fast alle vom Register bestimmten Orte sind verortet (99,9 %) und fast 99 % aller Orte, die das Buch nennt; die meisten übrigen sind Lehen und Banne ohne einen einzelnen Ort. Unsichere Bestimmungen und Lagen sind im Seitenfeld vermerkt, und jeder Eintrag verweist auf seine Seite in der Ausgabe von 1870.",
      "Namen, die der Scan entstellt hat, wurden auf den Seitenbildern nachgelesen: die Ortsnamen, die Stichwörter des Registers mit ihren Gemeinden und Kantonen und der Text der Einträge, geleitet von einer zweiten OCR-Lesung (Tesseract), den Schreibweisen von 1594 in DicoTopo und der Tabelle der alten Formen der Herausgeber. Für das Deutsche Bellistum entschieden Henri Hiegels Bestimmungen (Le bailliage d'Allemagne de 1600 à 1632, 1961, wie sie der Atlas des Deutschen Bellistums verzeichnet) bei Orten, die das Register offenlässt. Die Verarbeitung, die Bestimmungen und diese Lesungen wurden mit Claude (Anthropic) erarbeitet und von Hand geprüft.",
      "Deutsche Namen sind die historischen deutschen Namen der Orte, wo es sie gibt (Bolchen für Boulay, Saargemünd für Sarreguemines). Die japanischen Namen sind die des Atlas des Deutschen Bellistums, wo ein Ort in beiden Atlanten vorkommt, sonst wie dort in Katakana geschrieben: in Frankreich nach der französischen, in Deutschland nach der deutschen Aussprache.",
    ] },
    { title: "Autor", paragraphs: [
      "Konzipiert, erarbeitet und geprüft von Siargey Kachanovich. Daten und Texte des Atlas stehen unter der Lizenz Creative Commons Namensnennung 4.0 (CC BY 4.0): Sie dürfen sie mit Quellenangabe weiterverwenden und bearbeiten. Der Code steht unter der MIT-Lizenz. Dies gilt nicht für das Buch und seine Ausgabe von 1870, die gemeinfrei sind, und nicht für die Grundkarte und die unten genannten Quellen, die ihren eigenen Bedingungen unterliegen.",
    ] },
    { title: "Quellen", paragraphs: [
      "Thierry Alix, Dénombrement du duché de Lorraine (1594), hg. H. L. et A. de B., Recueil de documents sur l'histoire de Lorraine, Nancy 1870 (gemeinfrei).",
      "Grundkarte © OpenStreetMap-Mitwirkende (ODbL), über OpenFreeMap. Ortsdaten aus Wikidata (CC0) und GeoNames (CC BY 4.0). Alte Ortsnamen aus DicoTopo, dem Dictionnaire topographique de la France (CTHS, École nationale des chartes und Archives nationales, dicotopo.cths.fr), unter der Licence Ouverte 2.0, Datenstand 5. Oktober 2026.",
    ] },
  ],
  ja: [
    { title: "本書について", paragraphs: [
      "1594年、ロレーヌ会計院長で公爵文書庫の管理者であった Thierry Alix は、公爵シャルル3世のために公国の記述を作成した。バイイ管区・代官区・管区・領ごとに、そこに含まれる都市・村・城・修道院を挙げ、公爵の直轄領・封土・教会領に分けている。",
      "原本は失われ、写本によって伝わる。そのひとつを「H. L. et A. de B.」と署名する編者が1870年に『ロレーヌ史料集』で刊行した。編者は2,487項目に番号を振り、旧地名表と、各項目を1870年の自治体に比定する地名索引を付した。本地図はこのパブリックドメインの版にもとづく。",
    ] },
    { title: "地図の見方", paragraphs: [
      "地図は1594年に Alix が記述した公国を示す。本書はひとつの時点を記述しているため、年表はない。",
      "二つの階層を区別している。行政区画（バイイ管区・代官区・管区・城代管区・バン・村長区）は公国全体を覆う。封建領（伯領・領・名のある封土・教会領）は自らに属する地のみを覆う。同じ範囲を区画と封建領が覆う場合は両方を記録して結びつけ、その根拠を詳細欄に示す。",
      "保有形態は本書の小見出しによる。Domaine（公爵の直轄領）、Fiedvez（封土）、Clergé（教会領）、そして公爵の保護下にある村である。一部のみ保有される地（「en partie」「pour la moitié」）には斜線を引く。",
      "範囲は概略である。本書は地名を挙げるが境界は示さない。位置の判明した各村に、他のどの村よりも近い土地を6 kmまで割り当て、領域の範囲はその村々の土地の和とした。公国内外の既知の他領（メスとメス周辺地、トゥール、ヴェルダン、司教の町ヴィックとモワイヤンヴィック、ランベルヴィレール、バカラ、リヴェルダン、ザールブリュッケン）では、本書に載らない現在の自治体の土地を公国から除いた。それ以外では本書の村々の間の土地は公国に属する。バロワや帝国領などさらに遠い土地は白地のままである。",
      "「集落」タブでは保有形態のほか、本書の主題別一覧を地図に示せる。都市、司教座聖堂と参事会教会、修道院、小修道院、托鉢・女子修道院、騎士団管区、そしてヴォージュの夏季放牧地（ショーム）である。ショームは Alix が代官区ごとに挙げており、地図ではジット数で代官区を濃淡表示する。",
    ] },
    { title: "データの作成", paragraphs: [
      "スキャンのOCR文字をページごとに読み、誤読を考慮して項目番号を復元し、見出しを二つの階層に分解した。各項目は番号と名前によって索引の編者による比定と照合し、編者の訂正を反映した。さらに両者を番号ごとに突き合わせ、索引の各番号が指す項目を確定した（誤読された番号は印刷面で読み直した）。複数の地を挙げる項目はそのすべてに属する。各地点には一覧・索引・旧表記表の表記をそれぞれ残している。地点は索引が示す自治体またはカントンの近くで Wikidata と GeoNames により位置を特定し、すべての位置をそれと照らし合わせた。さらにムルト（ルパージュ）、ムーズ（リエナール）、モーゼル（ブテイエ）、ヴォージュ（マリシャル）の地名辞典で各地の旧表記を検索した。これらはデータベースにない小村を挙げ、しばしば本書そのものを引用している（マリシャルは項目番号で引く）。辞典が索引の比定の誤りを示す場合はその比定に従ったが、詳細欄には索引の記述もそのまま示している。固有の位置をもたない小村は所属自治体に置き、中空の記号で描いている。",
      "索引が比定する地はほぼすべて（99.9%）、本書が挙げる地全体ではほぼ99%の位置が判明している。残りの多くは単一の所在地をもたない封土やバンである。不確かな比定や位置は詳細欄に示し、各項目には1870年版のページを付している。",
      "スキャンで崩れた名称はページ画像で読み直した。地名、索引の見出しとその自治体・カントン、項目の本文であり、二度目の OCR（Tesseract）、DicoTopo の1594年の表記、編者の旧表記表を手がかりとした。ドイツ・バイイ管区では、索引が未確定とする地をHenri Hiegel の比定（Le bailliage d'Allemagne de 1600 à 1632、1961年。ドイツ・バイイ管区アトラスに収録）によって確定した。処理の流れ、比定、これらの読み直しは Claude（Anthropic）とともに作業し、手作業で確認した。",
      "ドイツ語名は、歴史的なドイツ語名がある地ではそれを用いる（ブーレに対する Bolchen、サルグミーヌに対する Saargemünd）。日本語名は、両アトラスに共通する地ではドイツ・バイイ管区アトラスのものを用い、それ以外は同アトラスと同じくカタカナで表記した。フランスの地はフランス語読み、ドイツの地はドイツ語読みである。",
    ] },
    { title: "作成者", paragraphs: [
      "企画・データ作成・確認：Siargey Kachanovich。本アトラスのデータと文章はクリエイティブ・コモンズ 表示 4.0 ライセンス（CC BY 4.0）で公開する。出典を明記すれば再利用・改変できる。コードは MIT ライセンスで公開する。ただし、パブリックドメインである本書とその1870年版、ならびに背景地図と下記の出典は対象外であり、それぞれの条件に従う。",
    ] },
    { title: "出典", paragraphs: [
      "Thierry Alix, Dénombrement du duché de Lorraine (1594), éd. H. L. et A. de B., Recueil de documents sur l'histoire de Lorraine, Nancy, 1870（パブリックドメイン）。",
      "背景地図 © OpenStreetMap contributors (ODbL)、OpenFreeMap経由。地点データは Wikidata (CC0) と GeoNames (CC BY 4.0) による。旧地名は DicoTopo（Dictionnaire topographique de la France、CTHS・国立古文書学校・フランス国立公文書館、dicotopo.cths.fr、Licence Ouverte 2.0、2026年10月5日のデータ）による。",
    ] },
  ],
};

export function renderAbout(root: HTMLElement, data: Dataset, lang: Lang, store: Store): void {
  const c = data.meta.counts;
  const section = (s: Section) => [h("h3", {}, s.title), ...s.paragraphs.map((p) => h("p", {}, ...linkHistMap(p)))];
  // Alix and Hiegel compared comes after how the data was made, before the author and the sources.
  const sections = TEXT[lang];
  fill(root,
    h("article", { class: "about" },
      h("h2", {}, t("view_about", lang)),
      ...sections.slice(0, 3).flatMap(section),
      ...compareSection(data, lang, store),
      ...sections.slice(3).flatMap(section),
      h("p", { class: "muted" }, `${t("dataVersion", lang)} ${data.meta.version} · ${c.entries} ${t("entriesShown", lang)} · `
        + `${c.located}/${c.settlements} ${t("placesLocated", lang)} · ${c.territories} ${t("subTerritories", lang).toLowerCase()}`),
    ),
  );
}
