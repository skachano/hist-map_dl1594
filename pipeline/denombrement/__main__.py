import argparse

from denombrement import config


def main() -> None:
    parser = argparse.ArgumentParser(prog="denombrement")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("info", help="show paths and the source PDF")
    sub.add_parser("extract-text", help="Stage 1: PDF -> pages, parts, index, old forms, corrections in data/raw/")
    args = parser.parse_args()

    if args.cmd == "info":
        print(f"root:      {config.ROOT}")
        print(f"curated:   {config.CURATED_DIR}")
        print(f"web data:  {config.WEB_DATA_DIR}")
        try:
            print(f"source:    {config.source_pdf().name}")
        except FileNotFoundError as e:
            print(f"source:    missing ({e})")
    elif args.cmd == "extract-text":
        from denombrement.text import extract
        extract.run()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
