// The files of web/public/data/ (Stage 7, pipeline/denombrement/web_data.py), as the app sees them.
export type Lang = "en" | "fr" | "de" | "ja";
export type Names = Partial<Record<Lang, string>>;
export type Labels = Partial<Record<Lang, string>> & { hierarchy?: "admin" | "feudal" };

export interface Meta {
  year: number;
  source: string;
  version: string;
  counts: Record<string, number>;
  vocab: Record<string, Record<string, Labels>>;
}

export interface Parent {
  id: string;
  rel: "admin" | "feudal" | "ressort";
  share?: string;
}

/** A holding: tenure, holder (absent: not named in the book), share, the entries it rests on. */
export interface Holding {
  t: string;
  h?: string;
  share?: string;
  with?: string[];
  e: (number | string)[];
}

/** A spelling of a place: in the lists (with their entries), in the editor's index (with the
 *  numbers it sends the place to), or in the edition's table of old forms. */
export interface Spelling {
  s: string;
  src: "book" | "index" | "old";
  e?: (number | string)[];
}

export interface Place {
  id: string;
  kind: "settlement" | "territory";
  type: string;
  name: Names;
  /** territories: the seat as printed */
  variants?: string[];
  /** settlements: every spelling, by source */
  spell?: Spelling[];
  index?: { kind?: string; commune?: string; canton?: string; dept?: string };
  lat?: number;
  lon?: number;
  /** how sure the point is */
  geo?: "high" | "medium" | "low";
  /** placed at its commune */
  approx?: boolean;
  lost?: boolean;
  wd?: string;
  country?: string;
  /** territories: hierarchy, holders of a realm, the territory of the other hierarchy on the same land */
  h?: "admin" | "feudal";
  holder?: string[];
  counterpart?: string;
  basis?: string;
  parents?: Parent[];
  tenure?: string;
  hold?: Holding[];
  entries?: (number | string)[];
  pages?: string;
  conf?: string;
}

export interface Entry {
  no: number | string;
  text: string;
  name: string;
  desc?: string[];
  district?: string;
  realm?: string;
  section?: string;
  holders?: string[];
  share?: string;
  with?: string[];
  /** absent for the Dénombrement itself, else the thematic list */
  series?: string;
  order?: string;
  /** the place the entry is matched to; `also`: the other places the index sends to it */
  place?: string;
  also?: string[];
  /** its lines in the editor's index: the heading as printed, its page, the place it identifies;
   *  `np`: the line of its place, which doesn't print the entry's number */
  ix?: { s: string; p?: string; place?: string; np?: boolean }[];
  page?: string;
  conf?: string;
}

export interface Entity {
  id: string;
  type: string;
  name: Names;
  rank: number;
  holdings: number;
}

export interface Feature {
  id: string;
  theme: string;
  name: string;
  place?: string;
  attrs?: Record<string, string | number | string[]>;
  page?: string;
}

export interface Dataset {
  meta: Meta;
  places: Map<string, Place>;
  entries: Entry[];
  entryByNo: Map<number | string, Entry>;
  entities: Map<string, Entity>;
  features: Feature[];
  territories: GeoJSON.FeatureCollection;
  cells: GeoJSON.FeatureCollection;
}
