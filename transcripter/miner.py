import operator
import re
from enum import Enum
from typing import List, Type, IO
from datetime import datetime
import logging

from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBoxHorizontal
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage


logger = logging.getLogger(__name__)


class TextElement(object):
    """
    Represents a single text element on a page.
    """

    def __init__(self, page: int, bbox, text: str):
        self.page = page
        self.bbox = bbox
        self.text = text
        # self.column = self.evaluatSelfToSetType()

    def __repr__(self):
        return f"<Pg.{self.page:02} {self.bbox} {self.text}>"


class Line(object):
    """
    Represents a single line of a transcript page.
    """

    def __init__(self, page: int, line_number: int, start_position: float, text: str):
        self.page = page
        self.line_number = line_number
        self.text = text.strip()
        self.start_position = start_position
        # self.positions = set()
        # self.column = self.evaluatSelfToSetType()

    def __repr__(self):
        return f"Pg.{self.page:02} Ln: {self.line_number:02}, Start: {self.start_position}, Txt: {self.text}"


def MinePDFTranscript(
    pdfData: IO,
    left_margin: float = 0,
    right_margin: float = 0,
    bottom_margin: float = 0,
    top_margin: float = 0,
) -> List[Line]:

    document = pdfData
    transcript_lines: List[Line] = list()
    # Create resource manager
    rsrcmgr = PDFResourceManager()
    # Set parameters for analysis.

    # Parameters for layout analysis
    # Parameters:
    # char_margin – If two characters are closer together than this margin they are considered part of the same line. The margin is specified relative to the width of the character.
    # word_margin – If two characters on the same line are further apart than this margin then they are considered to be two separate words, and an intermediate space will be added for readability. The margin is specified relative to the width of the character.
    # line_margin – If two lines are are close together they are considered to be part of the same paragraph. The margin is specified relative to the height of a line.
    # boxes_flow – Specifies how much a horizontal and vertical position of a text matters when determining the order of text boxes. The value should be within the range of -1.0 (only horizontal position matters) to +1.0 (only vertical position matters). You can also pass None to disable advanced layout analysis, and instead return text based on the position of the bottom left corner of the text box.

    laparams = LAParams(
        line_overlap=0.5,  # Default 0.5; If two characters have more overlap than this they are considered to be on the same line. The overlap is specified relative to the minimum height of both characters.
        char_margin=0.5,  # Default 2.0
        line_margin=0.5,  # Default 0.5
        word_margin=0.0,  # Default 0.1
        boxes_flow=0.5,  # Default 0.5
        detect_vertical=False,  # If vertical text should be considered during layout analysis
        all_texts=False,
    )  # If layout analysis should be performed on text in figures.

    # Create a PDF page aggregator object.
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    for page in PDFPage.get_pages(document):
        interpreter.process_page(page)
        # receive the LTPage object for the page.
        layout = device.get_result()
        # print("Layout: " + str(layout.pageid))  # Actual Page ID, 1 based
        # print("Page: " + str(page.pageid))

        page_num = layout.pageid
        media_box = page.mediabox

        width: float = page.mediabox[2]
        height: float = page.mediabox[3]

        # print(f"media_box: {media_box}, width: {width}, height: {height}")

        elements_on_page: List[TextElement] = list()

        for element in layout:
            # print(element)
            # Only use LTTextBoxHorizontal Elements
            if isinstance(element, LTTextBoxHorizontal):

                bbox = element.bbox
                text = element.get_text()

                # x0: the distance from the left of the page to the left edge of the box.
                # y0: the distance from the bottom of the page to the lower edge of the box.
                # x1: the distance from the left of the page to the right edge of the box.
                # y1: the distance from the bottom of the page to the upper edge of the box.
                if bbox[0] > left_margin:
                    newElement = TextElement(page_num, element.bbox, text)
                    # print(f"Append TextElement: {newElement}")
                    elements_on_page.append(newElement)

        # print(f"Elements on Page:  {len(elements_on_page)}")
        _sortElements_on_page(elements_on_page)
        lines = _convert_elements_on_page_into_lines(elements_on_page)
        # print(f"Lines Extracted: {len(lines)}")
        filtered = _filter_lines(lines, width)
        # print(f"Filtered Lines: {len(filtered)}")
        transcript_lines.extend(filtered)

    # for l in transcript_lines:
    #     print(l)

    return transcript_lines


def _sortElements_on_page(elements: List[TextElement]):
    # Sort by Page, Line/Height, then Column
    # The bbox value is (x0,y0,x1,y1).

    # x0: the distance from the left of the page to the left edge of the box.
    # y0: the distance from the bottom of the page to the lower edge of the box.
    # x1: the distance from the left of the page to the right edge of the box.
    # y1: the distance from the bottom of the page to the upper edge of the box.
    elements.sort(key=lambda x: (x.page, -x.bbox[3], x.bbox[0]))


def _filter_lines(lines: List[Line], page_width: float) -> List[Line]:

    # x_positions = set()
    # for l in lines:
    #     x_positions.add(l.start_position)

    # sorted_by_x = sorted(x_positions)
    # print(f"Distinct Positions on X: {sorted_by_x}")

    filtered_lines = list()
    for l in lines:

        # Exclude Page Numbers
        if l.start_position > page_width / 2:
            # This should be a line number on the right half of page
            continue

        # All filters passed
        # add positions
        # l.positions = x_positions
        # append
        filtered_lines.append(l)

    return filtered_lines


def _convert_elements_on_page_into_lines(
    elements: List[TextElement], fudge_factor: int = 10
) -> List[Line]:
    """Sort elements on a page into individual lines"""

    lines: List[Line] = list()

    last_top = 0

    stage: List[TextElement] = list()

    for i, e in enumerate(elements):
        # print(f"Loop {i},\nStaged Len: {len(stage)}, Element: {e}")
        if i == 0:
            # First loop, we need to set last_top.
            # print(f"First loop last_top: {e.bbox[3]}")
            last_top = e.bbox[3]

        current_top = e.bbox[3]
        difference = last_top - current_top
        # print(f"Last {last_top} - current {current_top} = Difference: {difference}")

        if difference < fudge_factor:
            # This is within the fudge factor
            # This should be considered the same line
            # print("Same line. Append")
            stage.append(e)
        else:
            # This is a new line
            # print("New line.")
            # Sort
            stage.sort(key=lambda x: (x.page, x.bbox[0]))

            first_element_on_line = stage[0]
            line_number = 0
            full_line_text = ""
            start_postion = 0
            try:
                line_number = int(first_element_on_line.text)

                start_postion = stage[1].bbox[0]
                # Skip the first, because it is the line number
                for z in stage[1:]:
                    full_line_text += z.text
            except ValueError:
                # ValueError: invalid literal for int()
                # The first is not a line number, so something weird is happening
                # Just leave it alone.
                for z in stage:
                    full_line_text += z.text
                start_postion = first_element_on_line.bbox[0]
            except IndexError:
                # IndexError: list index out of range
                # This could happen when len(stage) < 2
                # so less than two elements on the line
                start_postion = first_element_on_line.bbox[0]
                for z in stage:
                    full_line_text += z.text

            # There are sometimes random line breaks in a single line string
            # This can happen when redactions occur on a line. So when a name has
            # been redacted and replaced with "W-7" it will be
            # Pg.08 Ln: 24, Start: 171.0, Txt: b'Q.   Is that consistent with the testimony -- or excuse'
            # Pg.08 Ln: 25, Start: 135.0, Txt: b'me, not the testimony -- is that consistent with what'
            # Pg.09 Ln: 01, Start: 174.071, Txt: b'W-7\ntold you about what he was doing that day?'
            # Pg.09 Ln: 02, Start: 171.0, Txt: b'A.   Yes, sir.'
            # Pg.09 Ln: 03, Start: 171.0, Txt: b'Q.   And in fact, are you aware that\nW-7\nsaid'
            # Pg.09 Ln: 04, Start: 135.0, Txt: b'that he was walking his dog and walked by an individual that'

            # if it is the same line, we should replace any line breaks with " "
            full_line_text = full_line_text.replace("\n", " ")

            # First element should be a line number
            new_line = Line(
                page=e.page,
                line_number=line_number,
                start_position=start_postion,
                text=full_line_text,
            )
            lines.append(new_line)
            # Reset our var
            last_top = current_top
            stage.clear()
            # This element is the start of the next line
            stage.append(e)
        # print(f"End Loop {i} #########")

    return lines


if __name__ == "__main__":
    logging.basicConfig(
        filename="miner.log",
        filemode="w",
        format="%(levelname)s.%(name)s - %(message)s",
        level=logging.DEBUG,
    )

    document = open(f"./test2.pdf", "rb")
    MinePDFTranscript(document)
