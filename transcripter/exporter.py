import logging
import re
from typing import List, Type, IO
from transcripter.miner import Line
import pprint

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


qa = re.compile("^[AQ]\.\s+")  # Capture Q. or A.
speaker = re.compile(
    "^[A-Z\.\s]+:"
)  # Capture new speaker, ie., COURT:, MR. CLARK: BY MR. SMITH:
# Capture new speaker, ie., BY MR. SMITH:
by_mr_smith = re.compile("^BY [A-Z\.\s]+:$")
empty_line_number = re.compile("^[0-9]{1,2}$")


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

    print(f"Q and A Position: {q_position}")
    print(f"Speakers Position: {speaker_position}")
    print(f"Continuation Position: {continuation_position}")
    print(f"Line Number Position: {line_number_position}")

    return (continuation_position, q_position, speaker_position)


def lines_to_paragraphs(
    lines: List[Line],
    include_page_numbers: bool = True,
    include_line_numbers: bool = True,
):

    pos_continue, pos_question, pos_speaker = _analyze_lines(lines)

    # So rather than compare two very specific floats,
    # lets add 1.5 and cast to an integer
    # anything less than this x value, will be a continuation line
    continue_integer = int(pos_continue + 1.5)

    paragraphs = list()
    new_paragraph = ""
    current_page_number = 0
    starting_line = 0
    ending_line = 0

    for l in lines:

        # Check if this line is a new line or a continuing line
        # Assumes all lines to the left of the continue_integer are
        # continuations of the same paragraph.
        if l.start_position <= continue_integer:
            # print(f"Continue {l.start_position} less than {continue_integer}")
            # continue
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
                paragraphs.append(f"[{starting_line}-{ending_line}]  {new_paragraph}")
            else:
                # Just the paragraph
                paragraphs.append(new_paragraph)
                # print(f"Append: {new_paragraph}")

            # Reset Vars
            starting_line = l.line_number  # The starting line of this new paragraph
            ending_line = l.line_number
            new_paragraph = l.text
            # Check if starts with  Q. or A.
            if qa.search(l.text):
                # REMOVE Q. A. , + Add break
                # Q. A. constantly being read aloud is distracting and interupts the flow
                new_paragraph = qa.sub("", l.text)

            # Check if new speaker, ie. MR. NAME:
            if speaker.search(l.text):
                # New Speaker
                pass

        if include_page_numbers:
            # Add Page Numbers as Separate paragraphs in the list
            if current_page_number != l.page:
                # New page reached.
                # If the current page number has changed, add
                # the current page number into the list of paragraphs.
                # print(f"This page: {current_page_number}, last page: {l.page}")
                paragraphs.append(f"[PAGE: {l.page}]")

        # Update Current Page Number
        current_page_number = l.page

    return paragraphs
