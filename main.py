import logging
import pathlib

from transcripter.miner import MinePDFTranscript
from transcripter.exporter import lines_to_paragraphs

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logging.basicConfig(
        filename="miner.log",
        filemode="w",
        format="%(levelname)s.%(name)s - %(message)s",
        level=logging.INFO,
    )

    pdfminerSixLogger = logging.getLogger("pdfminer")
    pdfminerSixLogger.setLevel(logging.ERROR)

    input_path = pathlib.Path("./test2.pdf")
    document = open(input_path, "rb")
    lines = MinePDFTranscript(document)
    paragraphs = lines_to_paragraphs(lines)

    with open(f"{input_path}.txt", "w") as file:
        for par in paragraphs:
            file.write(f"{par}\n")

    print(f"Processed {len(lines)} lines. FINISHED.")
