import logging
from pathlib import Path
import os
import sys

from miner import MinePDFTranscript
from exporter import lines_to_paragraphs

logger = logging.getLogger(__name__)


def convert_file(file_path: Path, pgNum=True, lnNum=True, qa=True, date=False):
    if not file_path.is_file():
        logger.warning(f"Path is not a file: {file_path}")
        return

    if file_path.suffix != ".pdf":
        logger.warning(f"This file is not a PDF: {file_path}")

    logger.info(f"Processing {file_path.name}")

    document = open(file_path, "rb")
    lines = MinePDFTranscript(document)
    paragraphs = lines_to_paragraphs(
        lines,
        include_page_numbers=pgNum,
        include_line_numbers=lnNum,
        include_q_a_next_to_line_number=qa,
        include_date_with_page_numbers=date,
    )

    txt_file = file_path.with_suffix(".txt")
    with open(txt_file, "w") as file:
        for par in paragraphs:
            file.write(f"{par}\n")

    logger.info(f"Processed {len(lines)} transcript lines.")


def main(path_str: str, pgNum=True, lnNum=True, qa=True, date=False):
    path = Path(path_str)

    if path.is_dir():
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                p = Path(root, name)
                # only look at PDF documents
                if p.suffix == ".pdf" or p.suffix == ".PDF":
                    try:
                        convert_file(p, pgNum=pgNum, lnNum=lnNum,
                                     qa=qa, date=date)
                    except Exception as err:
                        logger.error(
                            f"ERROR: Unable to Process File: {p.__str__()}")
                        logger.error(err)

                else:
                    logger.info(
                        f"Skipping file with invalid suffix: {p.suffix}")
    else:
        # Single File
        if path.is_file():
            convert_file(path)


if __name__ == "__main__":
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(levelname)s.%(name)s - %(message)s")
    handler.setFormatter(formatter)
    root.addHandler(handler)

    logging.basicConfig(
        filename="miner.log",
        filemode="w",
        format="%(levelname)s.%(name)s - %(message)s",
        level=logging.INFO,
    )

    pdfminerSixLogger = logging.getLogger("pdfminer")
    pdfminerSixLogger.setLevel(logging.ERROR)

    import argparse

    parser = argparse.ArgumentParser(
        prog="Transcript Extractor",
        description="Extract and format text from PDF transcripts.",
        epilog="For more information.",
    )
    # positional argument
    parser.add_argument(
        "path",
        help="A path to a PDF transcript or directory contiaining PDF transcripts.",
    )

    # parser.add_argument(
    #     "--include-page-numbers",
    #     required=False,
    #     type=bool,
    #     help="Whether the program should include page numbers in the output txt file. The default is True."
    # )
    # parser.add_argument('--include_date_with_page_numbers')
    args = parser.parse_args()
    print(args.path)

    main(args.path)
    # main("./omar")

    print(f"COMPLETE")
