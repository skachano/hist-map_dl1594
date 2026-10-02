import argparse
from pathlib import Path

from denombrement import config


def main() -> None:
    parser = argparse.ArgumentParser(prog="denombrement")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("info", help="show paths and the source PDF")
    sub.add_parser("extract-text", help="Stage 1: PDF -> pages, parts, index, old forms, corrections in data/raw/")
    val = sub.add_parser("validate", help="Stage 2: check data/curated/ against the schema and vocabularies")
    val.add_argument("--dir", type=Path, default=config.CURATED_DIR, help="dataset directory (default data/curated)")
    val.add_argument("--info", action="store_true", help="also print information-level findings")
    sub.add_parser("schema", help="Stage 2: export JSON Schema per table to data/schema/")
    sub.add_parser("parse", help="Stage 3: parse the Dénombrement into data/extracted/ (entries, territories, chaumes)")
    args = parser.parse_args()

    if args.cmd == "info":
        print(f"root:      {config.ROOT}")
        print(f"curated:   {config.CURATED_DIR}")
        print(f"web data:  {config.WEB_DATA_DIR}")
        try:
            print(f"source:    {config.source_pdf().name}")
        except FileNotFoundError as e:
            print(f"source:    missing ({e})")
    elif args.cmd == "validate":
        from denombrement.data import store, validate
        ds = store.load(args.dir)
        issues = validate.validate(ds)
        for issue in issues:
            if issue.level != "info" or args.info:
                print(issue)
        for line in validate.coverage(ds):
            print(line)
        counts = {lvl: sum(i.level == lvl for i in issues) for lvl in ("error", "warning", "info")}
        print(f"{counts['error']} error(s), {counts['warning']} warning(s), {counts['info']} info")
        raise SystemExit(1 if counts["error"] else 0)
    elif args.cmd == "schema":
        from denombrement.data import schema
        for path in schema.export():
            print(path.relative_to(config.ROOT))
    elif args.cmd == "parse":
        from collections import Counter

        from denombrement.parse import features, report, structure
        result = structure.run()
        chaumes = features.run()
        report.write(result, chaumes)
        main_entries = [e for e in result.entries if e.series == "main"]
        print(f"entries: {len(result.entries)} ({len(main_entries)} in the Dénombrement), "
              f"territories: {len(result.territories)}, chaumes: {len(chaumes)}")
        for issue in result.issues:
            print(f"  {issue}")
        print(f"sections: {dict(Counter(e.section for e in main_entries))}")
        print(f"-> {(config.EXTRACTED_DIR / 'parse_report.md').relative_to(config.ROOT)}")
    elif args.cmd == "extract-text":
        from denombrement.text import extract
        extract.run()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
