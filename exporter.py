import logging
import re
from typing import List, Type, IO
from miner import Line
import pprint
from datetime import datetime

logger = logging.getLogger(__name__)


pp = pprint.PrettyPrinter(indent=4)


class Speaker(object):
    """
    Represents a section of text with a primary speaker.
    """

    def __init__(self, primary_speaker: str):
        self.primary_speaker = primary_speaker
        #  self.judges: List[CCR_Judge] = list()
        self.paragraphs: List[str] = list()

    def __repr__(self):
        return f"Speaker: {self.primary_speaker}"


# qa = re.compile("^[AQ]\.\s+")  # Capture Q. or A.
# qa = re.compile("^[AQ]")  # Capture Q. or A.
qa = re.compile("^[AQ][\s\.]+")  # Loose and Greedy
speaker = re.compile(
    "^[A-Z\.\s]+:"
)  # Capture new speaker, ie., COURT:, MR. CLARK: BY MR. SMITH:
# Capture new speaker, ie., BY MR. SMITH:
by_mr_smith = re.compile("^BY [A-Z\.\s]+:$")
empty_line_number = re.compile("^[0-9]{1,2}$")
date_line_re = re.compile(
    "^(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday), (January|February|March|April|May|June|July|August|September|October|November|December) ([\d]+), ([\d]{4})$"
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
    Return the first value from the sorted tuples of x position.
    The tuples are first sorted by the frequency of the starting positon.
    The position that occurs most frequently should be the correct start
    position for regex used to create the dictionary.

    Returns the start position which occurs most frequently in the values_dict.
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

    q_a_dict = dict()
    speaker_dict = dict()
    empty_lines_dict = dict()
    other_dict = dict()

    for l in lines:
        if qa.search(l.text):
            # Q. A. Detected
            _update_dict(q_a_dict, l, "New Questions Position")

        elif speaker.search(l.text):
            # New speaker detected
            # MR. SMITH:
            _update_dict(speaker_dict, l, "New Speaker Position")

        elif empty_line_number.search(l.text):
            # Check for remaining empty line numbers
            # Note: Line number are already filtered out by the miner module,
            # however, empty lines are left in.
            _update_dict(empty_lines_dict, l, "Empty Line Number Position")

        else:
            # After Questions, Answers, and new speakers, continuation
            # lines should be the most frequent start position we encounter.
            _update_dict(other_dict, l, "New Other Position")

    q_position = _get_result(q_a_dict)
    speaker_position = _get_result(speaker_dict)
    continuation_position = _get_result(other_dict)
    line_number_position = _get_result(empty_lines_dict)

    logger.debug(f"Q and A Position: {q_position}")
    logger.debug(f"Speakers Position: {speaker_position}")
    logger.debug(f"Continuation Position: {continuation_position}")
    logger.debug(f"Line Number Position: {line_number_position}")

    return (line_number_position, continuation_position, q_position, speaker_position)


def lines_to_paragraphs(
    lines: List[Line],
    include_page_numbers: bool = True,
    include_line_numbers: bool = False,
    include_q_a_next_to_line_number: bool = False,
    include_date_with_page_numbers: bool = False,
):

    pos_line_number, pos_continue, pos_question, pos_speaker = _analyze_lines(lines)

    # So rather than compare two very specific floats,
    # lets add 1.5 and cast to an integer
    # anything less than this x value, will be a continuation line
    continue_integer = int(pos_continue + 1.5)

    paragraphs = list()
    new_paragraph = ""
    current_page_number = 0
    starting_line = 0
    ending_line = 0
    date_of_transcript: datetime | None = None

    for l in lines:

        if current_page_number == 1:
            # If this is the first page. Lets look for the
            # date of this transcript.
            if date_line_re.search(l.text):
                # Transcript date found
                date_of_transcript = datetime.strptime(l.text, "%A, %B %d, %Y")
                logger.debug(f"Date: {date_of_transcript.strftime('%A, %B %d, %Y')}")

        # Check if this line is a new line or a continuing line
        # Assumes all lines to the left of the continue_integer are
        # continuations of the same paragraph.
        if l.start_position <= continue_integer:
            # print(f"Continue {l.start_position} less than {continue_integer}")
            # continue
            if l.start_position <= pos_line_number:
                # This is an empty line number to the far left of the page
                # print(
                #     f"Skipping empty line. Page: {current_page_number}, Text: {l.text}"
                # )
                pass
                # Note: We need to pass here. You cannot use continue because
                # we need the rest of the loop to be evaluated.
            else:
                new_paragraph = f"{new_paragraph} {l.text}"
                # Update the ending line number each time a continuation line
                # is evaluated.
                ending_line = l.line_number

        else:
            # This is to the right of the continuation integer.
            # This should be a new paragraph.

            # This is the start of a new paragraph, so deal with the
            # pre-existing paragraph before checking the new one

            if include_line_numbers:
                # Insert the line numbers in side square brackets
                # Note: Some tts reader ignore text inside square brackets.
                # Most listeners will not want to hear the line numbers read for
                # each new paragraph.

                line_nums = f"{starting_line}-{ending_line}"
                line_nums = "{:<5}".format(line_nums)

                line_nums = f"[{line_nums}]"
                paragraphs.append(f"{line_nums}  {new_paragraph}")
            else:
                # Just the paragraph
                paragraphs.append(new_paragraph)
                # logger.debug(f"Append: {new_paragraph}")

            # START NEW PARAGRAPH
            # Reset Vars
            starting_line = l.line_number  # The starting line of this new paragraph
            ending_line = l.line_number
            new_paragraph = l.text
            # Check if starts with  Q. or A.
            mo_qa = qa.search(l.text)
            # Check if Q. or A.
            if mo_qa:
                # Just REMOVE Q. A.
                # Q. A. constantly being read aloud is distracting and interupts the flow
                new_paragraph = qa.sub("", new_paragraph)

                if include_q_a_next_to_line_number:
                    # Add Question or Answer back in but with brackets
                    new_paragraph = f"[{mo_qa.group().strip()}] {new_paragraph}"

            # Check if new speaker, ie. MR. NAME:
            if speaker.search(new_paragraph):
                # New Speaker
                pass

        if include_page_numbers:
            # Add Page Numbers as Separate paragraphs in the list
            if current_page_number != l.page:
                # New page reached.
                # If the current page number has changed, add
                # the current page number into the list of paragraphs.
                # print(f"This page: {current_page_number}, last page: {l.page}")
                if include_date_with_page_numbers:
                    # Check that date_of_transcript is not None
                    if date_of_transcript:
                        paragraphs.append(
                            f"[PAGE: {l.page}, Date: {date_of_transcript.strftime('%A, %B %d, %Y')}]"
                        )
                    else:
                        paragraphs.append(f"[PAGE: {l.page}]")
                else:
                    paragraphs.append(f"[PAGE: {l.page}]")

        # Update Current Page Number
        current_page_number = l.page

    return paragraphs
