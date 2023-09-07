import logging
import re
from typing import List, Type, IO, Dict, Set
from miner import Line
import pprint
from datetime import datetime

logger = logging.getLogger(__name__)


pp = pprint.PrettyPrinter(indent=4)


def _format_line_numbers(starting_line: int, ending_line: int, starting_page: int, ending_page: int) -> str:

    if starting_page != ending_page:
        # Starting page is not the same as the ending page.
        line_nums = f"{starting_page}:{starting_line}-{ending_page}:{ending_line}"
    else:
        # Start page and end page are the same, no need to add the end page.
        line_nums = f"{starting_page}:{starting_line}-{ending_line}"

    # line_nums = f"{starting_line}-{ending_line}"
    # line_nums = "{:<5}".format(line_nums)

    # [16:25-17:4]
    line_nums = "{:<10}".format(line_nums)

    line_nums = f"[{line_nums}]"

    return line_nums


class Speaker(object):
    """
    Represents a section of text with a primary speaker.
    """

    def __init__(self, name: str, page: int):
        self.name = name
        self.pages: Set[int] = set([page])
        #  self.judges: List[CCR_Judge] = list()
        # self.paragraphs: List[str] = list()

    def update_pages(self, page):
        self.pages.add(page)

    def __repr__(self):
        return f"<SPEAKER: {self.name} Pages: {self.pages}>"


class Paragraph(object):
    """
    Represents a paragraph of text with a primary speaker.
    """

    def __init__(self):
        self.text = ""
        self.speaker: Speaker = None
        self.page_start: int = 0
        self.page_end: int = 0
        self.line_start: int = 0
        self.line_end: int = 0
        self.question: bool = False
        self.answer: bool = False

    def __repr__(self) -> str:
        return f"<PARAGRAPH: {self.name} Pages: {self.pages}>"

    def __str__(self, include_line_numbers: bool = True, include_q_a_next_to_line_number: bool = True) -> str:

        txt = self.text

        if include_q_a_next_to_line_number:

            if self.question:
                # Add Question or Answer back in but with brackets
                txt = f"[Q] {txt}"

            if self.answer:
                # Add Question or Answer back in but with brackets
                txt = f"[A] {txt}"

        if include_line_numbers:
            line_nums = _format_line_numbers(
                self.line_start, self.line_end, self.page_start, self.page_end)
            return f"{line_nums}  {txt}"

    def add_text(self, text: str):
        if self.text == "":
            self.text = text.strip()
        else:
            self.text = f"{self.text} {text.strip()}"

    def remove_q_a(self):
        # Remove Q. or A. from text
        # Just REMOVE Q. A.
        # Q. A. constantly being read aloud is distracting and interupts the flow
        # print(bytes(self.text, encoding="utf-8"))
        res = qa.sub("", self.text)
        self.text = res


# qa = re.compile("^[AQ]\.\s+")  # Capture Q. or A.
# qa = re.compile("^[AQ]")  # Capture Q. or A.
qa = re.compile("^[AQ][\s\.]+")  # Loose and Greedy
speaker_regex = re.compile(
    "^[A-Z\.\s]+:"
)  # Capture new speaker, ie., COURT:, MR. CLARK: BY MR. SMITH:
# Capture new speaker, ie., BY MR. SMITH:
by_mr_smith_regex = re.compile("^BY [A-Z\.\s]+:$")
empty_line_number = re.compile("^[0-9]{1,2}$")
date_line_re = re.compile(
    "(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday), (January|February|March|April|May|June|July|August|September|October|November|December) ([\d]+), ([\d]{4})$"
)


def _update_dict(this_dict: dict, l: Line, note) -> dict:
    """
    Creates a dictionary of the starting x positions of the lines
    which match the regex.  Later, we can use frequency counting
    to see what the x position value should be.
    """
    if l.start_position in this_dict:
        # This position has already occured.
        # Just update the count
        this_dict[l.start_position] = this_dict[l.start_position] + 1
    else:
        # New Position Detected
        # print(note, l)
        this_dict[l.start_position] = 1
    return this_dict


def _get_result(values_dict: dict) -> float | None:
    """
    Returns the start position which occurs most frequently in the values_dict.

    Return the first value from the sorted tuples of x position.
    The tuples are first sorted by the frequency of the starting positon.
    The position that occurs most frequently should be the correct start
    position for regex used to create the dictionary.

    """

    # Sort tuple (start_position, number of occurences)
    sorted_tuples = sorted(values_dict.items(), key=lambda kv: -kv[1])

    if len(sorted_tuples) > 0:
        # return the most frequent start position for this dictionary
        return sorted_tuples[0][0]
    else:
        return None


def _analyze_lines(lines: List[Line]):
    """
    Analyze the lines of a transcript and return the starting positions
    of the Q. A.'s, the new speakers, and the continuation line.
    """

    logger.info("Analyzing Lines")
    # logger.debug(lines)
    # logger.debug(f"Lines: {pprint.pprint(lines)}")
    # logger.debug(f"Lines:\n{pprint.pformat(lines)}")

    q_a_dict = dict()
    speaker_dict = dict()
    empty_lines_dict = dict()
    other_dict = dict()

    for l in lines:
        logger.debug(l)
        if qa.search(l.text):
            # Q. A. Detected
            logger.debug("Q. A. Detected")
            _update_dict(q_a_dict, l, "New Questions Position")

        elif speaker_regex.search(l.text):
            # New speaker detected
            # MR. SMITH:
            logger.debug("New speaker detected")
            _update_dict(speaker_dict, l, "New Speaker Position")

        elif empty_line_number.search(l.text):
            # Check for remaining empty line numbers
            # Note: Line number are already filtered out by the miner module,
            # however, empty lines are left in.
            logger.debug("Empty Line Number Detected")
            _update_dict(empty_lines_dict, l, "Empty Line Number Position")

        else:
            # After Questions, Answers, and new speakers, continuation
            # lines should be the most frequent start position we encounter.
            logger.debug("Other (Continuation) Line Detected")
            _update_dict(other_dict, l, "New Other Position")

    logger.debug(f"q_a_dict:\n{pprint.pformat(q_a_dict)}")
    logger.debug(f"speaker_dict:\n{pprint.pformat(speaker_dict)}")
    logger.debug(f"empty_lines_dict:\n{pprint.pformat(empty_lines_dict)}")
    logger.debug(f"other_dict:\n{pprint.pformat(other_dict)}")

    q_position = _get_result(q_a_dict)
    logger.info(f"q_position: {q_position}")
    speaker_position = _get_result(speaker_dict)
    logger.info(f"speaker_position: {speaker_position}")
    continuation_position = _get_result(other_dict)
    logger.info(f"continuation_position: {continuation_position}")
    line_number_position = _get_result(empty_lines_dict)
    logger.info(f"line_number_position: {line_number_position}")

    if not line_number_position:
        logger.error(
            f"Line number position not detected. This is an error. The system must be able to detect the position of the line number.")

        logger.error(empty_lines_dict)
        # No empty line numbers detected.

        # Assume the empty line number position is X less than continuation_position
        line_number_position = continuation_position - 4
        # raise Exception("Line number not detected. Aborting.")

    logger.debug(f"Q and A Position: {q_position}")
    logger.debug(f"Speakers Position: {speaker_position}")
    logger.debug(f"Continuation Position: {continuation_position}")
    logger.debug(f"Line Number Position: {line_number_position}")

    return (line_number_position, continuation_position, q_position, speaker_position)


def lines_to_paragraphs(
    lines: List[Line],
):

    logger.info("Starting lines_to_paragraphs")

    logger.debug(f"Lines:\n{pprint.pformat(lines)}")

    pos_line_number, pos_continue, pos_question, pos_speaker = _analyze_lines(
        lines)

    # So rather than compare two very specific floats,
    # lets add 1.5 and cast to an integer
    # anything less than this x value, will be a continuation line
    continue_integer = int(pos_continue + 1.5)
    logger.info(f"Continuation Position Detected at: {continue_integer}")

    paragraphs = list()
    speakers: Dict[str, Speaker] = dict()
    list_of_paragraph_objects: List[Paragraph] = list()

    new_paragraph = ""
    current_paragraph_object = Paragraph()
    current_speaker = None
    current_questioner = None
    current_procedure = None  # None, Direct, Cross
    current_page_number = 0
    starting_line = 0
    starting_page = 0
    ending_line = 0
    date_of_transcript: datetime | None = None

    for i, l in enumerate(lines):
        logger.debug(f"Line: {l}")
        if current_page_number == 1:
            # If this is the first page. Lets look for the
            # date of this transcript.
            # logger.info(l.text)
            date_match = date_line_re.search(l.text)
            if date_match:
                # Transcript date found
                date_of_transcript = datetime.strptime(
                    date_match.group(0), "%A, %B %d, %Y")
                logger.info(
                    f"Transcript Date Found: {date_of_transcript.strftime('%A, %B %d, %Y')}")

        # Check if this line is a new line or a continuing line
        # Assumes all lines to the left of the continue_integer are
        # continuations of the same paragraph.
        if l.start_position <= continue_integer:
            logger.debug(
                f"Continue {l.start_position} less than {continue_integer}")

            if l.start_position <= pos_line_number:
                # This is an empty line number to the far left of the page
                # print(
                #     f"Skipping empty line. Page: {current_page_number}, Text: {l.text}"
                # )
                pass
                # Note: We need to pass here. You cannot use continue because
                # we need the rest of the loop to be evaluated.
            else:
                # Update the ending line number each time a continuation line
                # is evaluated.
                current_paragraph_object.add_text(l.text)
                current_paragraph_object.line_end = l.line_number
                current_paragraph_object.page_end = l.page

        else:
            # NEW PARAGRAPH

            # This is to the right of the continuation integer.
            # This should be a new paragraph.
            logger.debug(
                f"New Paragraph Detected: {l.start_position} greater than {continue_integer}")

            # This is the start of a new paragraph, so deal with the
            # pre-existing paragraph before checking the new one
            list_of_paragraph_objects.append(current_paragraph_object)
            logger.debug(f"Appending Paragraph: {current_paragraph_object}")

            # Reset Variables for New Paragraph
            current_paragraph_object = Paragraph()  # New Paragraph
            current_paragraph_object.add_text(l.text)
            current_paragraph_object.page_start = l.page
            current_paragraph_object.line_start = l.line_number
            current_paragraph_object.page_end = l.page
            current_paragraph_object.line_end = l.line_number

            # Check if new speaker, ie. MR. NAME:
            mo_speaker_regex = speaker_regex.search(l.text)
            if mo_speaker_regex:
                # New Speaker
                # logger.info("New speaker detected.")
                # speakers.add(mo_speaker_regex.group(0))
                this_speaker = mo_speaker_regex.group(0)

                if speakers.__contains__(this_speaker):
                    # update existing speaker
                    existing_speaker = speakers[this_speaker]
                    existing_speaker.update_pages(l.page)
                    current_speaker = existing_speaker
                else:

                    if this_speaker == "APPEARANCES:":
                        # Ignore "APPEARANCES:" which get detected as a speaker
                        pass
                    else:
                        # create new speaker
                        new_speaker = Speaker(this_speaker, page=l.page)
                        speakers[this_speaker] = new_speaker
                        current_speaker = new_speaker

                current_paragraph_object.speaker = current_speaker

                if this_speaker.startswith("BY "):
                    current_questioner = current_speaker

            # elif new_paragraph == "EXAMINATION":
            #     # Grand Jury Transcripts just have EXAMINATION
            #     current_procedure = "EXAMINATION"
            #     new_paragraph = f"[***********] {new_paragraph}"

            # elif new_paragraph == "DIRECT EXAMINATION":
            #     current_procedure = "DIRECT EXAMINATION"
            #     new_paragraph = f"[***********] {new_paragraph}"

            # elif new_paragraph == "CROSS-EXAMINATION":
            #     current_procedure = "CROSS-EXAMINATION"
            #     new_paragraph = f"[***********] {new_paragraph}"

            # elif new_paragraph == "REDIRECT-EXAMINATION":
            #     current_procedure = "REDIRECT-EXAMINATION"
            #     new_paragraph = f"[***********] {new_paragraph}"

            else:
                # Check if starts with  Q. or A.
                mo_qa = qa.search(l.text)
                # Check if Q. or A.
                if mo_qa:
                    q_or_a = mo_qa.group().strip()

                    if q_or_a == "Q":
                        # Add Question or Answer back in but with brackets
                        current_paragraph_object.question = True
                        current_paragraph_object.remove_q_a()

                    if q_or_a == "A":
                        current_paragraph_object.answer = True
                        current_paragraph_object.remove_q_a()

            # LAST LINE
            # If Last Line Then Add IT AS PARAGRAPH
            if len(lines) == i + 1:
                logger.debug(f"Appending Last Paragraph: {new_paragraph}")
                list_of_paragraph_objects.append(current_paragraph_object)

        # Update Current Page Number
        current_page_number = l.page

    logger.debug(f"Paragraphs:\n{pprint.pformat(paragraphs)}")
    logger.info(f"Detected Speakers:\n{pprint.pformat(speakers)}")
    return list_of_paragraph_objects
