// About & sources: where Alix (1594) and Henri Hiegel's bailliage d'Allemagne (1600–1632, as the atlas
// hist_map records it) part, in tables. Places link to the map, Alix's divisions to the Territories
// view; Hiegel's units are named, since this atlas doesn't have them.
import type { Dataset, Lang } from "../data/types";
import { label, name, t } from "../i18n";
import type { Store } from "../state/store";
import { h } from "./dom";
import { openPlace, showOnMap } from "./navigate";

type Text = Record<Lang, string>;

export const HIST_MAP_URL = "https://skachano.github.io/hist-map_gb1600";
export const HIST_MAP = /German Bailiwick atlas|atlas du bailliage d'Allemagne|Atlas des Deutschen Bellistums|ドイツ・バイイ管区アトラス/;

/** A text with the German Bailiwick atlas (hist_map), named in any language, linked to it. */
export function linkHistMap(text: string): (Node | string)[] {
  const m = HIST_MAP.exec(text);
  if (!m) return [text];
  return [text.slice(0, m.index), h("a", { href: HIST_MAP_URL, target: "_blank", rel: "noopener" }, m[0]),
    ...linkHistMap(text.slice(m.index + m[0].length))];
}
/** A run of text: plain, translated, a place of this atlas (a link), or one of Hiegel's units. */
type Part = string | Text | { place: string } | { hiegel: string };
/** One of Hiegel's units or places, with his pages. */
type Cite = { parts: Part[]; pages?: string };

/** Hiegel's units, named as hist_map names them. */
export const HIEGEL: Record<string, Text> = {
  "office-sierck": { en: "Office of Sierck", fr: "Office de Sierck", de: "Amt Sierck", ja: "シエルク管区" },
  "office-boulay": { en: "Office of Boulay", fr: "Office de Boulay", de: "Amt Bolchen", ja: "ブレ管区" },
  "office-vaudrevange": { en: "Office of Wallerfangen", fr: "Office de Vaudrevange", de: "Amt Wallerfangen", ja: "ヴァラーファンゲン管区" },
  "office-siersberg": { en: "Office of Siersburg", fr: "Office de Siersberg", de: "Amt Siersburg", ja: "ジールスベルク管区" },
  "condominium-merzig-saargau": { en: "Condominium of Saargau-Merzig", fr: "Condominium de Saargau-Merzig",
    de: "Kondominium Saargau-Merzig", ja: "ザールガウ＝メルツィヒ共同統治地" },
  saargau: { en: "Saargau", fr: "Saargau", de: "Saargau", ja: "ザールガウ" },
  "office-merzig": { en: "Office of Merzig", fr: "Office de Merzig", de: "Amt Merzig", ja: "メルツィヒ管区" },
  "office-schaumberg": { en: "Office of Schaumberg", fr: "Office de Schaumberg", de: "Amt Schaumberg", ja: "シャウムベルク管区" },
  "office-sarreguemines": { en: "Office of Sarreguemines", fr: "Office de Sarreguemines", de: "Amt Saargemünd", ja: "サルグミーヌ管区" },
  "office-dieuze": { en: "Office of Dieuze", fr: "Office de Dieuze", de: "Amt Duß", ja: "ディウーズ管区" },
  "office-puttelange": { en: "Office of Puttelange", fr: "Office de Puttelange", de: "Amt Püttlingen", ja: "ピュトランジュ管区" },
  "office-berus": { en: "Office of Berus", fr: "Office de Berus", de: "Amt Berus", ja: "ベールス管区" },
  "office-morhange": { en: "Office of Morhange", fr: "Office de Morhange", de: "Amt Mörchingen", ja: "モランジュ管区" },
  "office-faulquemont": { en: "Office of Faulquemont", fr: "Office de Faulquemont", de: "Amt Falkenberg", ja: "フォルクモン管区" },
  "office-forbach": { en: "Office of Forbach", fr: "Office de Forbach", de: "Amt Forbach", ja: "フォルバック管区" },
  "county-bitche": { en: "County of Bitche", fr: "Comté de Bitche", de: "Grafschaft Bitsch", ja: "ビッチュ伯領" },
  "office-hombourg-haut": { en: "Office of Hombourg-Haut", fr: "Office de Hombourg-Haut", de: "Amt Oberhomburg", ja: "オンブール＝オー管区" },
  "advocacy-saint-avold": { en: "Advocacy of Saint-Avold", fr: "Vouerie de Saint-Avold", de: "Vogtei Sankt Avold", ja: "サンタヴォル教会守護領" },
  "castellany-marsal": { en: "Castellany of Marsal", fr: "Châtellenie de Marsal", de: "Kellerei Marsal", ja: "マルサル城代管区" },
  "provostship-sarrebourg": { en: "Provostship of Sarrebourg", fr: "Prévôté de Sarrebourg", de: "Schultheißerei Saarburg", ja: "サールブール代官区" },
  "lordship-sarreck": { en: "Lordship of Sarreck", fr: "Seigneurie de Sarreck", de: "Herrschaft Sarreck", ja: "サレック領" },
  "office-sarralbe": { en: "Office of Sarralbe", fr: "Office de Sarralbe", de: "Amt Saaralben", ja: "サラルブ管区" },
  "office-phalsbourg": { en: "Office of Phalsbourg", fr: "Office de Phalsbourg", de: "Amt Pfalzburg", ja: "ファルスブール管区" },
  "lordship-fenetrange": { en: "Lordship of Fénétrange", fr: "Seigneurie de Fénétrange", de: "Herrschaft Finstingen", ja: "フェネトランジュ領" },
  "principality-lixheim": { en: "Principality of Lixheim", fr: "Principauté de Lixheim", de: "Fürstentum Lixheim", ja: "リクサイム侯国" },
  "county-sarrewerden": { en: "County of Saarwerden", fr: "Comté de Sarrewerden", de: "Grafschaft Saarwerden", ja: "サールヴェルデン伯領" },
  "marquisate-faulquemont": { en: "Marquisate of Faulquemont", fr: "Marquisat de Faulquemont", de: "Markgrafschaft Falkenberg", ja: "フォルクモン侯爵領" },
  "county-boulay": { en: "County of Boulay", fr: "Comté de Boulay", de: "Grafschaft Bolchen", ja: "ブレ伯領" },
  "county-dalem": { en: "County of Dalem", fr: "Comté de Dalem", de: "Grafschaft Dalem", ja: "ダレム伯領" },
  "lordship-puttelange": { en: "Lordship of Puttelange", fr: "Seigneurie de Puttelange", de: "Herrschaft Püttlingen", ja: "ピュトランジュ領" },
  "lordship-forbach": { en: "Lordship of Forbach", fr: "Seigneurie de Forbach", de: "Herrschaft Forbach", ja: "フォルバック領" },
};

const TITLE: Text = { en: "Alix and Hiegel compared", fr: "Alix et Hiegel comparés", de: "Alix und Hiegel im Vergleich",
  ja: "Alix と Hiegel の比較" };

const INTRO: Text = {
  en: "Henri Hiegel's Le bailliage d'Allemagne de 1600 à 1632 (1961) describes the German bailiwick a few years after Alix; the German Bailiwick atlas records it. Set side by side for 1600, the two place most of the settlements they share in the same unit. The tables give where they part: units under other names, lands Alix keeps out of the bailiwicks, villages filed under different offices, and the places whose identification here follows Hiegel. Places link to the map and Alix's divisions to the Territories view; Hiegel's pages are given after his units.",
  fr: "Le bailliage d'Allemagne de 1600 à 1632 d'Henri Hiegel (1961) décrit le bailliage quelques années après Alix ; l'atlas du bailliage d'Allemagne le reprend. Mis côte à côte pour 1600, les deux placent la plupart de leurs localités communes dans la même circonscription. Les tableaux disent où ils divergent : des circonscriptions sous d'autres noms, des terres qu'Alix laisse hors des bailliages, des villages rangés sous d'autres offices, et les lieux dont l'identification suit ici Hiegel. Les lieux renvoient à la carte et les circonscriptions d'Alix à la vue Territoires ; les pages de Hiegel suivent ses circonscriptions.",
  de: "Henri Hiegels Le bailliage d'Allemagne de 1600 à 1632 (1961) beschreibt das Deutsche Bellistum wenige Jahre nach Alix; der Atlas des Deutschen Bellistums verzeichnet es. Für 1600 nebeneinandergestellt, ordnen beide die meisten ihrer gemeinsamen Orte demselben Bezirk zu. Die Tabellen zeigen, wo sie auseinandergehen: Bezirke unter anderen Namen, Gebiete, die Alix außerhalb der Bellistümer führt, Dörfer unter anderen Ämtern und die Orte, deren Bestimmung hier Hiegel folgt. Orte führen zur Karte, Alix' Bezirke zur Ansicht Territorien; Hiegels Seiten stehen nach seinen Bezirken.",
  ja: "Henri Hiegel『Le bailliage d'Allemagne de 1600 à 1632』（1961年）は、Alix の数年後のドイツ・バイイ管区を記述しており、ドイツ・バイイ管区アトラスがそれを収録している。1600年について並べると、両者に共通する集落の大半は同じ区画に属する。以下の表は両者の相違を示す。名称の異なる区画、Alix がバイイ管区の外に置く地、異なる管区に記された村、そして本アトラスが Hiegel の比定に従った地である。地名は地図に、Alix の区画は「領域」表示にリンクする。Hiegel のページは区画名の後に示す。",
};

const COL = {
  alix: { en: "Alix (1594)", fr: "Alix (1594)", de: "Alix (1594)", ja: "Alix（1594年）" },
  hiegel: { en: "Hiegel (1600)", fr: "Hiegel (1600)", de: "Hiegel (1600)", ja: "Hiegel（1600年）" },
  settlement: { en: "Settlement", fr: "Localité", de: "Ort", ja: "集落" },
  note: { en: "Note", fr: "Remarque", de: "Anmerkung", ja: "備考" },
  alixSpelling: { en: "Alix", fr: "Alix", de: "Alix", ja: "Alix" },
  index: { en: "Editors' index", fr: "Table des éditeurs", de: "Register der Herausgeber", ja: "編者の索引" },
  here: { en: "Here", fr: "Ici", de: "Hier", ja: "本アトラス" },
  hiegelOnly: { en: "Hiegel", fr: "Hiegel", de: "Hiegel", ja: "Hiegel" },
} satisfies Record<string, Text>;

// --- 1. Units: Alix's divisions of the bailiwick and Hiegel's in 1600 ---

const UNITS_TITLE: Text = { en: "Divisions", fr: "Circonscriptions", de: "Bezirke", ja: "区画" };
export const UNITS: [string[], string[]][] = [
  [["provostship-sierck"], ["office-sierck"]],
  [["office-boulay"], ["office-boulay"]],
  [["office-vaudrevange"], ["office-vaudrevange"]],
  [["office-siersberg"], ["office-siersberg"]],
  [["district-saargau", "district-merzig"], ["condominium-merzig-saargau"]],
  [["office-schaumbourg"], ["office-schaumberg"]],
  [["office-sarreguemines"], ["office-sarreguemines"]],
  [["castellany-dieuze", "castellany-marimont"], ["office-dieuze"]],
  [["district-puttelange"], ["office-puttelange"]],
  [["district-beaurains"], ["office-berus"]],
  [["district-morhange"], ["office-morhange"]],
  [["district-faulquemont"], ["office-faulquemont"]],
  [["district-forbach"], ["office-forbach"]],
];
const UNITS_AFTER: Record<Lang, Part[]> = {
  en: ["Alix gives ", { place: "district-merzig" }, " and ", { place: "district-saargau" },
    ", which Lorraine shared with the elector of Trier, as two districts; Hiegel as one condominium of two halves. ",
    { place: "castellany-marimont" }, ", a castellany in Alix, is a lordship of the ", { hiegel: "office-dieuze" }, " in Hiegel."],
  fr: ["Alix donne ", { place: "district-merzig" }, " et ", { place: "district-saargau" },
    ", que la Lorraine partageait avec l'électeur de Trèves, comme deux circonscriptions ; Hiegel comme un condominium en deux moitiés. ",
    { place: "castellany-marimont" }, ", châtellenie chez Alix, est chez Hiegel une seigneurie de l'", { hiegel: "office-dieuze" }, "."],
  de: ["Merzig (", { place: "district-merzig" }, ") und den Saargau (", { place: "district-saargau" },
    "), die Lothringen mit dem Kurfürsten von Trier teilte, führt Alix als zwei Bezirke, Hiegel als ein Kondominium aus zwei Hälften. ",
    { place: "castellany-marimont" }, ", bei Alix eine Kellerei, ist bei Hiegel eine Herrschaft im ", { hiegel: "office-dieuze" }, "."],
  ja: ["Alix は、ロレーヌがトリーア選帝侯と共有したメルツィヒとザールガウを二つの区画（", { place: "district-merzig" }, "、",
    { place: "district-saargau" }, "）とし、Hiegel は二つの半分からなる一つの共同統治地とする。Alix では城代管区である",
    { place: "castellany-marimont" }, "は、Hiegel では", { hiegel: "office-dieuze" }, "の中の領である。"],
};

// --- 2. Lands Alix keeps out of the bailiwicks ---

const OUTSIDE_TITLE: Text = { en: "Lands outside Alix's bailiwicks", fr: "Terres hors des bailliages d'Alix",
  de: "Gebiete außerhalb von Alix' Bellistümern", ja: "Alix がバイイ管区の外に置く地" };
const OUTSIDE_INTRO: Text = {
  en: "Alix files these among the lands \"qui ne sont pas de bailliages\" (1870 ed., pp. 34, 107–115). Hiegel counts them in the bailiwick in 1600, but as contested: their subjects claimed not to belong to it (p. 11).",
  fr: "Alix les range parmi les terres « qui ne sont pas de bailliages » (éd. 1870, p. 34, 107-115). Hiegel les compte dans le bailliage en 1600, mais contestées : leurs sujets prétendaient ne pas en faire partie (p. 11).",
  de: "Alix führt sie unter den Gebieten, „qui ne sont pas de bailliages“ (Ausg. 1870, S. 34, 107–115). Hiegel zählt sie 1600 zum Bellistum, doch umstritten: ihre Untertanen bestritten, dazuzugehören (S. 11).",
  ja: "Alix はこれらを「バイイ管区に属さない地」（1870年版 p. 34, 107–115）に分類する。Hiegel は1600年のバイイ管区に含めるが、帰属は争われていた。住民は管区に属さないと主張した（p. 11）。",
};
export const OUTSIDE: { alix: string[]; hiegel: Cite[]; note: Text }[] = [
  { alix: ["district-bitche"], hiegel: [{ parts: [{ hiegel: "county-bitche" }], pages: "9, 11–12, 21–22" }], note: {
    en: "United to the duchy in 1572; in 1594 the receiver Jean Bosch reported that it was not part of the bailiwick; settled with Hanau-Lichtenberg in 1606.",
    fr: "Uni au duché en 1572 ; en 1594, le receveur Jean Bosch rapporte qu'il n'est pas du bailliage ; accord avec Hanau-Lichtenberg en 1606.",
    de: "1572 mit dem Herzogtum vereinigt; 1594 meldete der Rezeptor Jean Bosch, es gehöre nicht zum Bellistum; Vergleich mit Hanau-Lichtenberg 1606.",
    ja: "1572年に公国に統合。1594年に収税官ジャン・ボッシュはバイイ管区に属さないと報告した。1606年にハーナウ＝リヒテンベルクと和解。" } },
  { alix: ["castellany-hombourg-et-saint-avold"], hiegel: [{ parts: [{ hiegel: "office-hombourg-haut" }], pages: "11, 21, 63, 101" },
    { parts: [{ hiegel: "advocacy-saint-avold" }], pages: "11" }], note: {
    en: "Bought from the bishop of Metz in 1581; still an imperial fief of the bishop, exempt from ducal charges, with appeals to Vic and the Imperial Chamber.",
    fr: "Achetée à l'évêque de Metz en 1581 ; toujours fief impérial de l'évêque, exempte des charges ducales, les appels allant à Vic et à la Chambre impériale.",
    de: "1581 vom Bischof von Metz gekauft; weiterhin Reichslehen des Bischofs, frei von herzoglichen Lasten, mit Berufung nach Vic und an das Reichskammergericht.",
    ja: "1581年にメス司教から購入。なお司教の帝国封土で、公爵の負担を免れ、上訴はヴィックと帝国最高法院へ向かった。" } },
  { alix: ["town-district-marsal"], hiegel: [{ parts: [{ hiegel: "castellany-marsal" }], pages: "10–11, 21–22" }], note: {
    en: "Bought from the bishop of Metz in 1593.", fr: "Achetée à l'évêque de Metz en 1593.",
    de: "1593 vom Bischof von Metz gekauft.", ja: "1593年にメス司教から購入。" } },
  { alix: ["town-district-sarrebourg"], hiegel: [{ parts: [{ hiegel: "provostship-sarrebourg" }], pages: "11, 21" }], note: {
    en: "Bought from the bishop of Metz in 1562; paid the aid of 1585 to the bailiwick of Nancy.",
    fr: "Achetée à l'évêque de Metz en 1562 ; paya l'aide de 1585 au bailliage de Nancy.",
    de: "1562 vom Bischof von Metz gekauft; zahlte die Beihilfe von 1585 an das Bellistum Nancy.",
    ja: "1562年にメス司教から購入。1585年の援助金はナンシー・バイイ管区に納めた。" } },
  { alix: ["district-sarreck"], hiegel: [{ parts: [{ hiegel: "lordship-sarreck" }], pages: "9, 11, 22" }], note: {
    en: "Paid the aid of 1585 to the bailiwick of Nancy.", fr: "Paya l'aide de 1585 au bailliage de Nancy.",
    de: "Zahlte die Beihilfe von 1585 an das Bellistum Nancy.", ja: "1585年の援助金はナンシー・バイイ管区に納めた。" } },
  { alix: ["district-sarralbe"], hiegel: [{ parts: [{ hiegel: "office-sarralbe" }], pages: "11, 21" }], note: {
    en: "Bought from the bishop of Metz in 1562.", fr: "Achetée à l'évêque de Metz en 1562.",
    de: "1562 vom Bischof von Metz gekauft.", ja: "1562年にメス司教から購入。" } },
  { alix: ["district-phalsbourg"], hiegel: [{ parts: [{ hiegel: "office-phalsbourg" }], pages: "11, 21" }], note: {
    en: "Bought in 1583; not subject to the aid of 1585.", fr: "Achetée en 1583 ; non soumise à l'aide de 1585.",
    de: "1583 gekauft; nicht zur Beihilfe von 1585 verpflichtet.", ja: "1583年に購入。1585年の援助金は課されなかった。" } },
];
const OUTSIDE_AFTER: Record<Lang, Part[]> = {
  en: ["Hiegel also counts the ", { hiegel: "lordship-fenetrange" }, " (pp. 9, 22), most of whose villages Alix doesn't name, and lands added later: the ",
    { hiegel: "principality-lixheim" }, " in 1623, the ", { hiegel: "county-sarrewerden" }, " and the ", { hiegel: "marquisate-faulquemont" },
    " in 1629. Two villages of Alix's bailiwick of Nancy, ", { place: "chicourt" }, " (", { place: "provostship-amance" }, ") and ",
    { place: "lezey" }, " (", { place: "provostship-einville" }, "), were reckoned to the ", { hiegel: "office-dieuze" },
    " by its accountants from 1600 to 1620 (p. 74)."],
  fr: ["Hiegel compte aussi la ", { hiegel: "lordship-fenetrange" }, " (p. 9, 22), dont Alix ne nomme pas la plupart des villages, et des terres acquises plus tard : la ",
    { hiegel: "principality-lixheim" }, " en 1623, le ", { hiegel: "county-sarrewerden" }, " et le ", { hiegel: "marquisate-faulquemont" },
    " en 1629. Deux villages du bailliage de Nancy chez Alix, ", { place: "chicourt" }, " (", { place: "provostship-amance" }, ") et ",
    { place: "lezey" }, " (", { place: "provostship-einville" }, "), furent comptés à l'", { hiegel: "office-dieuze" },
    " par ses comptables de 1600 à 1620 (p. 74)."],
  de: ["Hiegel zählt auch die ", { hiegel: "lordship-fenetrange" }, " (S. 9, 22), deren Dörfer Alix meist nicht nennt, und später erworbene Gebiete: das ",
    { hiegel: "principality-lixheim" }, " 1623, die ", { hiegel: "county-sarrewerden" }, " und die ", { hiegel: "marquisate-faulquemont" },
    " 1629. Zwei Dörfer von Alix' Bellistum Nancy, ", { place: "chicourt" }, " (", { place: "provostship-amance" }, ") und ",
    { place: "lezey" }, " (", { place: "provostship-einville" }, "), rechneten die Rechnungsführer des ", { hiegel: "office-dieuze" },
    " von 1600 bis 1620 zu ihrem Amt (S. 74)."],
  ja: ["Hiegel はさらに", { hiegel: "lordship-fenetrange" }, "（p. 9, 22。Alix はその村の大半を挙げない）と、のちに加わった地、1623年の",
    { hiegel: "principality-lixheim" }, "、1629年の", { hiegel: "county-sarrewerden" }, "と", { hiegel: "marquisate-faulquemont" },
    "を含める。Alix ではナンシー・バイイ管区の二村、", { place: "chicourt" }, "（", { place: "provostship-amance" }, "）と",
    { place: "lezey" }, "（", { place: "provostship-einville" }, "）は、1600年から1620年まで", { hiegel: "office-dieuze" },
    "の会計官によって同管区に算入された（p. 74）。"],
};

// --- 3. Villages both place in the bailiwick, in different units ---

const DIFFER_TITLE: Text = { en: "Villages in different units", fr: "Villages dans des circonscriptions différentes",
  de: "Dörfer in verschiedenen Bezirken", ja: "異なる区画に置かれた村" };
const DIFFER_INTRO: Text = {
  en: "Alix lists under each office its domain, its fiefs and its church lands, and some of these lie in another office's land; this atlas files a place in every office that lists it. Hiegel files a village in the office it lies in, though he too lists such holdings under an office (Schaumberg's at Harlingen, Mondorf and Wehingen, p. 14).",
  fr: "Alix donne sous chaque office son domaine, ses fiefs et son clergé, dont certains sont sur les terres d'un autre office ; cet atlas range un lieu dans chaque office qui le donne. Hiegel range un village dans l'office où il se trouve, même s'il donne aussi de tels biens sous un office (ceux de Schaumberg à Harlingen, Mondorf et Wehingen, p. 14).",
  de: "Alix führt unter jedem Amt seine Domäne, seine Lehen und sein Kirchengut, die zum Teil auf dem Gebiet eines anderen Amts liegen; dieser Atlas ordnet einen Ort jedem Amt zu, das ihn nennt. Hiegel ordnet ein Dorf dem Amt zu, in dem es liegt, auch wenn er solche Besitzungen ebenfalls unter einem Amt aufführt (die Schaumbergs in Harlingen, Mondorf und Wehingen, S. 14).",
  ja: "Alix は各管区の下に、その直轄領・封土・教会領を挙げるが、その一部は他の管区の土地にある。本アトラスは、ある地をそれを挙げるすべての管区に含める。Hiegel は村をその所在する管区に置く。ただし Hiegel も、そうした保有地を管区の下に挙げることがある（シャウムベルクのハルリンゲン、モンドルフ、ヴェヒンゲンの保有地、p. 14）。",
};
export const DIFFER: { title: Text; rows: { place: string; entries: number[]; hiegel: Cite[]; note?: Record<Lang, Part[]> }[] }[] = [
  { title: { en: "Church lands and fiefs listed under another office", fr: "Clergé et fiefs donnés sous un autre office",
    de: "Kirchengut und Lehen unter einem anderen Amt", ja: "他の管区の下に挙げられた教会領・封土" }, rows: [
    { place: "harlingen", entries: [1464, 1506], hiegel: [{ parts: [{ hiegel: "office-merzig" }], pages: "14, 53" }] },
    { place: "mondorf", entries: [1460, 1505], hiegel: [{ parts: [{ hiegel: "saargau" }], pages: "14, 53, 55" },
      { parts: [{ hiegel: "office-siersberg" }], pages: "53" }], note: {
      en: ["Alix: \"partie dudict Sargaw et partie de l'office de Sirques\" (Sierck); Hiegel gives the other part to Siersberg."],
      fr: ["Alix : « partie dudict Sargaw et partie de l'office de Sirques » (Sierck) ; Hiegel donne l'autre partie à Siersberg."],
      de: ["Alix: „partie dudict Sargaw et partie de l'office de Sirques“ (Sierck); Hiegel gibt den anderen Teil Siersberg."],
      ja: ["Alix：「partie dudict Sargaw et partie de l'office de Sirques」（シエルク）。Hiegel は残りの部分をジールスベルクとする。"] } },
    { place: "wehingen", entries: [1458, 1527], hiegel: [{ parts: [{ hiegel: "saargau" }], pages: "14, 53, 55" }] },
    { place: "mettlach", entries: [1428], hiegel: [{ parts: [{ hiegel: "office-merzig" }], pages: "13, 54" }] },
    { place: "keuchingen", entries: [1429], hiegel: [{ parts: [{ hiegel: "office-merzig" }], pages: "13, 54" }] },
    { place: "tenteling", entries: [1577, 1585], hiegel: [{ parts: [{ hiegel: "office-forbach" }], pages: "17" }] },
    { place: "heckenransbach", entries: [1578], hiegel: [{ parts: [{ hiegel: "office-puttelange" }], pages: "17" }], note: {
      en: ["\"Rausspach\" is Heckenransbach by the editors' correction, in place of Bliesransbach, a village of Sarreguemines in Hiegel."],
      fr: ["« Rausspach » est Heckenransbach par la correction des éditeurs, au lieu de Bliesransbach, village de Sarreguemines chez Hiegel."],
      de: ["„Rausspach“ ist nach der Berichtigung der Herausgeber Heckenransbach statt Bliesransbach, bei Hiegel ein Dorf von Saargemünd."],
      ja: ["「Rausspach」は編者の訂正によりヘッケンランスバッハとされ、ブリースランスバッハ（Hiegel ではサルグミーヌの村）ではない。"] } },
  ] },
  { title: { en: "Fiefs filed under different offices", fr: "Fiefs rangés sous des offices différents",
    de: "Lehen unter verschiedenen Ämtern", ja: "異なる管区に記された封土" }, rows: [
    { place: "titling", entries: [1386], hiegel: [{ parts: [{ hiegel: "office-sierck" }], pages: "81" }], note: {
      en: ["Hiegel lists Tütting among the fiefs of the office of Sierck with ", { place: "penning" }, " and ", { place: "buchingen" },
        " (p. 81), which Alix lists among Boulay's (1389, 1390)."],
      fr: ["Hiegel donne Tütting parmi les fiefs de l'office de Sierck avec ", { place: "penning" }, " et ", { place: "buchingen" },
        " (p. 81), qu'Alix donne parmi ceux de Boulay (1389, 1390)."],
      de: ["Hiegel führt Tütting unter den Lehen des Amts Sierck, mit ", { place: "penning" }, " und ", { place: "buchingen" },
        " (S. 81), die Alix unter denen von Bolchen nennt (1389, 1390)."],
      ja: ["Hiegel はテュッティングを", { place: "penning" }, "・", { place: "buchingen" },
        "とともにシエルク管区の封土に挙げる（p. 81）。Alix はこの二つをブレの封土に挙げる（1389、1390）。"] } },
  ] },
  { title: { en: "Doubtful identifications", fr: "Identifications douteuses", de: "Unsichere Bestimmungen", ja: "疑わしい比定" }, rows: [
    { place: "alzing", entries: [1269, 1335], hiegel: [{ parts: [{ hiegel: "office-berus" }], pages: "15, 59" }], note: {
      en: ["\"Auselingen\" and \"Anselnigen\" are Alzing in the editors' index; Hiegel's Alzing is in the lordship of Berus."],
      fr: ["« Auselingen » et « Anselnigen » sont Alzing dans la table des éditeurs ; l'Alzing de Hiegel est de la seigneurie de Berus."],
      de: ["„Auselingen“ und „Anselnigen“ sind im Register der Herausgeber Alzing; Hiegels Alzing gehört zur Herrschaft Berus."],
      ja: ["「Auselingen」と「Anselnigen」は編者の索引でアルザンとされる。Hiegel のアルザンはベールス領に属する。"] } },
    { place: "guerstling", entries: [1325, 1683], hiegel: [{ parts: [{ hiegel: "office-berus" }], pages: "15, 58" },
      { parts: [{ hiegel: "county-dalem" }], pages: "27" }], note: {
      en: ["\"Gersslingen\" (Berus) agrees with Hiegel; \"Gursingen\" (Sierck) is Guerstling only by the editors' index."],
      fr: ["« Gersslingen » (Berus) s'accorde avec Hiegel ; « Gursingen » (Sierck) n'est Guerstling que par la table des éditeurs."],
      de: ["„Gersslingen“ (Berus) stimmt mit Hiegel überein; „Gursingen“ (Sierck) ist Guerstling nur nach dem Register der Herausgeber."],
      ja: ["「Gersslingen」（ベールス）は Hiegel と一致する。「Gursingen」（シエルク）をゲルストランとするのは編者の索引のみである。"] } },
    { place: "velving", entries: [1394, 1681], hiegel: [{ parts: [{ hiegel: "office-boulay" }], pages: "16, 82" }], note: {
      en: ["\"Weiblingen\" (Boulay) agrees with Hiegel; \"Weyllingen\" (Berus) is Velving only by the editors' index."],
      fr: ["« Weiblingen » (Boulay) s'accorde avec Hiegel ; « Weyllingen » (Berus) n'est Velving que par la table des éditeurs."],
      de: ["„Weiblingen“ (Bolchen) stimmt mit Hiegel überein; „Weyllingen“ (Berus) ist Velving nur nach dem Register der Herausgeber."],
      ja: ["「Weiblingen」（ブレ）は Hiegel と一致する。「Weyllingen」（ベールス）をヴェルヴァンとするのは編者の索引のみである。"] } },
  ] },
];

// --- 4. Entries whose place here follows Hiegel ---

const FOLLOW_TITLE: Text = { en: "Identifications that follow Hiegel", fr: "Identifications qui suivent Hiegel",
  de: "Bestimmungen nach Hiegel", ja: "Hiegel に従った比定" };
const FOLLOW_INTRO: Text = {
  en: "Where the editors' index is wrong or leaves a place unlocated, this atlas follows Hiegel, as the German Bailiwick atlas records him.",
  fr: "Là où la table des éditeurs se trompe ou ne situe pas un lieu, cet atlas suit Hiegel, tel que le reprend l'atlas du bailliage d'Allemagne.",
  de: "Wo das Register der Herausgeber irrt oder einen Ort nicht verortet, folgt dieser Atlas Hiegel, wie der Atlas des Deutschen Bellistums ihn verzeichnet.",
  ja: "編者の索引が誤っている場合や地点を特定していない場合、本アトラスはドイツ・バイイ管区アトラスが収録する Hiegel に従う。",
};
export const FOLLOW: { entry: number; index: string; hiegel: Cite }[] = [
  { entry: 1653, index: "Honzrath (Haustadt)", hiegel: { parts: [{ hiegel: "lordship-puttelange" }] } },
  { entry: 1390, index: "Freyming (1590)", hiegel: { parts: [{ hiegel: "county-boulay" }], pages: "16, 81" } },
  { entry: 1389, index: "Bockange (Piblange)", hiegel: { parts: [{ hiegel: "county-boulay" }], pages: "16, 81" } },
  { entry: 1736, index: "Bubingen, de la seigneurie de Forbach", hiegel: { parts: [{ hiegel: "lordship-forbach" }] } },
  { entry: 1238, index: "—", hiegel: { parts: [{ hiegel: "office-sierck" }, ", ", { hiegel: "office-boulay" }], pages: "60" } },
  { entry: 1304, index: "Fliessborn", hiegel: { parts: ["Vry"], pages: "13" } },
  { entry: 1305, index: "Hasenholh", hiegel: { parts: ["Bettelainville"], pages: "13, 270" } },
  { entry: 1549, index: "Bleysspach", hiegel: { parts: ["Oberkirchen"], pages: "15, 57" } },
  { entry: 1733, index: "Dittelingen", hiegel: { parts: ["Bousbach"], pages: "17" } },
  { entry: 1341, index: "Pomern", hiegel: { parts: ["Kochem"], pages: "50" } },
  { entry: 2203, index: "Eyningen", hiegel: { parts: ["Vinningen"], pages: "104–105" } },
  { entry: 2211, index: "Eich", hiegel: { parts: ["Thaleischweiler"], pages: "18" } },
  { entry: 2218, index: "Ranschborn", hiegel: { parts: ["Eppenbrunn"], pages: "18, 104" } },
  { entry: 2219, index: "Stanwenstein", hiegel: { parts: ["Vinningen"], pages: "18, 104, 106" } },
];
const FOLLOW_AFTER: Record<Lang, Part[]> = {
  en: ["Where they still differ, the index stands: ", { place: "baldringen" }, " (\"Balderingen\", 1459) stays at Zerf, where the editors put it, though Hiegel's Baldringen is ",
    { place: "ballern" }, ", which Alix lists as \"Baldern\" (1448)."],
  fr: ["Là où ils divergent encore, la table est suivie : ", { place: "baldringen" }, " (« Balderingen », 1459) reste à Zerf, où le placent les éditeurs, bien que le Baldringen de Hiegel soit ",
    { place: "ballern" }, ", qu'Alix donne sous le nom de « Baldern » (1448)."],
  de: ["Wo sie weiter auseinandergehen, gilt das Register: ", { place: "baldringen" }, " („Balderingen“, 1459) bleibt bei Zerf, wohin die Herausgeber es setzen, obwohl Hiegels Baldringen ",
    { place: "ballern" }, " ist, das Alix als „Baldern“ führt (1448)."],
  ja: ["なお相違が残る場合は索引に従う。", { place: "baldringen" }, "（「Balderingen」、1459）は編者のとおりツェルフに置く。ただし Hiegel の Baldringen は",
    { place: "ballern" }, "であり、Alix はこれを「Baldern」（1448）として挙げる。"],
};

/** Every place of this atlas the section links to. */
export function linkedPlaces(): string[] {
  const parts: Part[] = [
    ...Object.values(UNITS_AFTER).flat(), ...Object.values(OUTSIDE_AFTER).flat(), ...Object.values(FOLLOW_AFTER).flat(),
    ...DIFFER.flatMap((g) => g.rows.flatMap((r) => Object.values(r.note ?? {}).flat())),
  ];
  return [...new Set([
    ...UNITS.flatMap(([alix]) => alix), ...OUTSIDE.flatMap((r) => r.alix), ...DIFFER.flatMap((g) => g.rows.map((r) => r.place)),
    ...parts.flatMap((p) => typeof p === "object" && "place" in p ? [p.place as string] : []),
  ])];
}

/** Every one of Hiegel's units the section names. */
export function namedUnits(): string[] {
  const cites = [...OUTSIDE.flatMap((r) => r.hiegel), ...DIFFER.flatMap((g) => g.rows.flatMap((r) => r.hiegel)),
    ...FOLLOW.map((r) => r.hiegel)];
  const parts: Part[] = [...cites.flatMap((c) => c.parts), ...Object.values(UNITS_AFTER).flat(), ...Object.values(OUTSIDE_AFTER).flat()];
  return [...new Set([...UNITS.flatMap(([, hiegel]) => hiegel),
    ...parts.flatMap((p) => typeof p === "object" && "hiegel" in p ? [p.hiegel as string] : [])])];
}

export function compareSection(data: Dataset, lang: Lang, store: Store): HTMLElement[] {
  const placeName = (id: string) => name(data.places.get(id)?.name, lang, id);
  const link = (id: string) => h("button", { class: "link", "data-place": id, onclick: () =>
    data.places.get(id)?.kind === "territory" ? openPlace(store, data, id) : showOnMap(store, id) }, placeName(id));
  const part = (p: Part): Node | string => typeof p === "string" ? p
    : "place" in p ? link(p.place) : "hiegel" in p ? HIEGEL[p.hiegel]?.[lang] ?? p.hiegel : p[lang];
  const pages = (p?: string) => p ? ` (${t("pages", lang)} ${p})` : "";
  const cite = (c: Cite) => [...c.parts.map(part), pages(c.pages)];
  const list = <T>(items: T[], each: (x: T) => (Node | string)[], sep = "; ") =>
    items.flatMap((x, i) => [i ? sep : "", ...each(x)]);
  // An entry of Alix's: its division, its section of the Dénombrement and its number.
  const entry = (no: number) => {
    const e = data.entryByNo.get(no);
    const section = e?.section && e.section !== "other" ? `, ${label(data.meta.vocab.sections[e.section], lang, e.section)}` : "";
    return [e?.district ? link(e.district) : "", `${section} (${t("entry", lang)} ${no})`];
  };
  const table = (head: Text[], rows: HTMLTableRowElement[]) =>
    h("div", { class: "table-wrap" }, h("table", { class: "matrix" },
      h("thead", {}, h("tr", {}, ...head.map((c) => h("th", { scope: "col" }, c[lang])))),
      h("tbody", {}, ...rows)));
  const para = (parts: Part[]) => h("p", {}, ...parts.map(part));
  return [
    h("h3", { id: "alix-hiegel" }, TITLE[lang]),
    h("p", {}, ...linkHistMap(INTRO[lang])),
    h("h4", {}, UNITS_TITLE[lang]),
    table([COL.alix, COL.hiegel], UNITS.map(([alix, hiegel]) => h("tr", {},
      h("td", {}, ...list(alix, (id) => [link(id)], ", ")), h("td", {}, hiegel.map((id) => HIEGEL[id][lang]).join(", "))))),
    para(UNITS_AFTER[lang]),
    h("h4", {}, OUTSIDE_TITLE[lang]),
    h("p", {}, ...linkHistMap(OUTSIDE_INTRO[lang])),
    table([COL.alix, COL.hiegel, COL.note], OUTSIDE.map((r) => h("tr", {},
      h("td", {}, ...list(r.alix, (id) => [link(id)], ", ")), h("td", {}, ...list(r.hiegel, cite)), h("td", {}, r.note[lang])))),
    para(OUTSIDE_AFTER[lang]),
    h("h4", {}, DIFFER_TITLE[lang]),
    h("p", {}, ...linkHistMap(DIFFER_INTRO[lang])),
    table([COL.settlement, COL.alix, COL.hiegel, COL.note], DIFFER.flatMap((g) => [
      h("tr", { class: "group" }, h("th", { scope: "colgroup", colspan: "4" }, g.title[lang])),
      ...g.rows.map((r) => h("tr", {},
        h("th", { scope: "row" }, link(r.place)), h("td", {}, ...list(r.entries, entry)), h("td", {}, ...list(r.hiegel, cite)),
        h("td", {}, ...(r.note?.[lang] ?? []).map(part)))),
    ])),
    h("h4", {}, FOLLOW_TITLE[lang]),
    h("p", {}, ...linkHistMap(FOLLOW_INTRO[lang])),
    table([{ en: "No.", fr: "n°", de: "Nr.", ja: "番号" }, COL.alixSpelling, COL.index, COL.here, COL.hiegelOnly], FOLLOW.map((r) => {
      const e = data.entryByNo.get(r.entry);
      return h("tr", {}, h("th", { scope: "row" }, String(r.entry)), h("td", {}, e?.name ?? ""), h("td", {}, r.index),
        h("td", {}, e?.place ? link(e.place) : ""), h("td", {}, ...cite(r.hiegel)));
    })),
    para(FOLLOW_AFTER[lang]),
  ];
}
