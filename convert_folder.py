import logging
from pathlib import Path

import os


from transcripter.miner import MinePDFTranscript
from transcripter.exporter import lines_to_paragraphs

logger = logging.getLogger(__name__)

logging.basicConfig(
    filename="miner.log",
    filemode="w",
    format="%(levelname)s.%(name)s - %(message)s",
    level=logging.INFO,
)

pdfminerSixLogger = logging.getLogger("pdfminer")
pdfminerSixLogger.setLevel(logging.ERROR)


def convert_file(file_path: Path):

    if not file_path.is_file():
        return

    if file_path.suffix != ".pdf":
        print("Not PDF")

    print(f"Processing {file_path.name}")

    document = open(file_path, "rb")
    lines = MinePDFTranscript(document)
    paragraphs = lines_to_paragraphs(
        lines,
        include_page_numbers=True,
        include_line_numbers=True,
        include_q_a_next_to_line_number=True,
        include_date_with_page_numbers=False,
    )

    txt_file = file_path.with_suffix(".txt")
    with open(txt_file, "w") as file:
        for par in paragraphs:
            file.write(f"{par}\n")

    print(f"Processed {len(lines)} lines. FINISHED.")


def main(dir):

    for root, dirs, files in os.walk(dir, topdown=False):
        for name in files:
            print(root, name)
            p = Path(root, name)
            # only look at PDF documents
            if p.suffix == ".pdf":
                convert_file(p)
            else:
                logger.info(f"Skipping file with suffix: {p.suffix}")
            # print(os.path.join(root, name))
        # for name in dirs:
        #     print(os.path.join(root, name))


if __name__ == "__main__":
    main("./turner")

    print(f"FINISHED.")
