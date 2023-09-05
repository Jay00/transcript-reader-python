import logging
from pathlib import Path
import os
import sys

from miner import MinePDFTranscript
from exporter import lines_to_paragraphs

logger = logging.getLogger(__name__)


def convert_file(file_path: Path,
                 pgNum: bool = True,
                 lnNum: bool = True,
                 qa: bool = True,
                 date: bool = True,
                 left_margin: float = 0,
                 right_margin: float = 0,
                 bottom_margin: float = 0,
                 top_margin: float = 0):
    logger.info(f"Processing {file_path.name}")

    # logger.info(
    #     f"convert_file received parameters:\npgNum: {pgNum}\nlnNum: {lnNum}\nqa: {qa}")

    if not file_path.is_file():
        logger.warning(f"Path is not a file: {file_path}")
        return

    if file_path.suffix != ".pdf":
        logger.warning(f"This file is not a PDF: {file_path}")

    # Open the document stream
    document = open(file_path, "rb")

    # Extract the lines
    lines = MinePDFTranscript(document, left_margin=left_margin,
                              right_margin=right_margin, bottom_margin=bottom_margin, top_margin=top_margin)
    paragraphs = lines_to_paragraphs(lines)

    txt_file = file_path.with_suffix(".txt")
    with open(txt_file, "w", encoding="utf-8") as file:
        for par in paragraphs:
            file.write(
                f"{par.__str__(include_line_numbers=lnNum, include_q_a_next_to_line_number=qa)}\n")

    logger.info(f"Processed {len(lines)} transcript lines.")


def main(path_str: str,
         pgNum=False,
         lnNum=True,
         qa=True,
         date=True,
         left_margin: float = 0,
         right_margin: float = 0,
         bottom_margin: float = 53,
         top_margin: float = 0):

    logger.info(f"Processing Path: {path_str}")
    logger.info(
        f"Received parameters:\
            \n\t\t\tpgNum: {pgNum} (include separate page numbers)\
            \n\t\t\tlnNum: {lnNum} (include line numbers)\
            \n\t\t\tqa: {qa} (include [Q.] or [A.]\
            \n\t\t\tdate: {date} (include dates (only works with include page numbers True))")
    path = Path(path_str)

    if path.is_dir():
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                p = Path(root, name)
                # only look at PDF documents
                if p.suffix == ".pdf" or p.suffix == ".PDF":
                    try:
                        convert_file(file_path=p, pgNum=pgNum, lnNum=lnNum,
                                     qa=qa, date=date, left_margin=left_margin, right_margin=right_margin, bottom_margin=bottom_margin, top_margin=top_margin)

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
            convert_file(file_path=path, pgNum=pgNum, lnNum=lnNum,
                         qa=qa, date=date, left_margin=left_margin, right_margin=right_margin, bottom_margin=bottom_margin, top_margin=top_margin)
        else:
            logger.warn("The provided path is not a file or directory.")


if __name__ == "__main__":
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(levelname)s.%(name)s:%(lineno)d - %(message)s")
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # create file handler which logs even debug messages
    fh = logging.FileHandler('transcript.log', mode="w", encoding="utf-8")
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(levelname)s.%(name)s:%(lineno)d - %(message)s")
    fh.setFormatter(formatter)
    # add the handlers to the logger
    root.addHandler(fh)

    # logging.basicConfig(
    #     filename="miner.log",
    #     filemode="w",
    #     format="%(levelname)s.%(name)s - %(message)s",
    #     level=logging.INFO,
    # )

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
