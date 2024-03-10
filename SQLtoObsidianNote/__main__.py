from SQLtoObsidianNote import generate_markdown_from_file

def cli():
    import argparse
    parser = argparse.ArgumentParser(description='Convert SQL to Obsidian notes', prog="SQLtoObsidianNote")
    parser.add_argument('input', type=str, help='The input SQL file')
    parser.add_argument('--output', type=str, help='The output directory', default=None)
    parser.add_argument('--dialect', type=str, help='The SQL dialect to use', default=None)
    args = parser.parse_args()

    generate_markdown_from_file(inputpath= args.input, outputpath=args.output, dialect=args.dialect)

if __name__ == "__main__":
    cli()