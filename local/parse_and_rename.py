from setup_data import ensure_data_dirs
from invoice_parser.cli import main

if __name__ == "__main__":
    ensure_data_dirs()
    main()
