import logging
import pathlib

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


def convert_file(file_path):
    input_file = pathlib.Path(file_path)
    document = open(input_path, "rb")
    lines = MinePDFTranscript(document)
    paragraphs = lines_to_paragraphs(lines)

    with open(f"{input_path}.txt", "w") as file:
        for par in paragraphs:
            file.write(f"{par}\n")

    print(f"Processed {len(lines)} lines. FINISHED.")


def main():

    for root, dirs, files in os.walk(".", topdown=False):
        for name in files:
            print(os.path.join(root, name))
        for name in dirs:
            print(os.path.join(root, name))


if __name__ == "__main__":
    main()

    print(f"FINISHED.")
