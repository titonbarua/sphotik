import os.path
import sqlite3
import logging
from collections import deque, Counter


class HistoryManager:

    SCHEMA = """
    CREATE TABLE history(
        roman_text TEXT NOT NULL,
        bangla_text TEXT NOT NULL,
        usecount INTEGER NOT NULL DEFAULT 1,

        PRIMARY KEY (roman_text, bangla_text)
    );
    """

    def __init__(
            self,
            histfilepath,
            input_generalizer=lambda x: x,
            session_history_size=1000,
            session_history_concern_size=20,):
        # An input generalizer is a function that may be used to
        # generalize the input data, so that history suggestions can be
        # laxed and fuzzy; trading their accuracy in return.
        self.input_generalizer = input_generalizer

        # Session history is an in-memory sequence of most recently used
        # words and their input texts. The most likely conversion of a word
        # can be deduced by filtering the sequence by respective input text
        # and doing a frequency analysis on the used output texts.
        self.session_history_concern_size = session_history_concern_size
        self.session_history = deque(maxlen=session_history_size)

        if not os.path.isfile(histfilepath):
            # Create the history file with proper permissions.
            with open(histfilepath, "w") as f:
                os.chmod(histfilepath, 0o600)

            # Write database schema.
            self.conn = sqlite3.connect(histfilepath)
            with self.conn:
                self.conn.execute(self.SCHEMA.strip())
        else:
            # Open an existing database.
            try:
                self.conn = sqlite3.connect(histfilepath)
            except sqlite3.DatabaseError as e:
                self.conn = None
                logging.warning(
                    "Failed to open history file '{}': {}"
                    .format(dbfilepath, e))

    QUERY_SEARCH = """
    SELECT bangla_text, usecount FROM history
    WHERE roman_text = :roman_text ORDER BY usecount DESC;
    """

    def _split_trailing_punctuations_from_cord(self, cord, puncs):
        split_at = len(cord)
        for bead in reversed(cord):
            if bead.v in puncs:
                split_at += -1
            else:
                break

        return cord[:split_at], cord[split_at:]

    def search_without_punctuation(self, parser):
        # Collect with-punctuation search results.
        results = self.search(parser.input_text)

        # Split the cord into a punctuation-less head
        # and a punctuation tail.
        head, tail = self._split_trailing_punctuations_from_cord(
            parser.cord, parser.rule.punctuations)

        # Workflow:
        #   - Extract strings from punctuation-less head
        #     and punctuation tail.
        #   - Find outputs for punctuation-trimmed input.
        #   - Join back the punctuation to the suggested output.
        input_t = parser.render_input_text(tail)
        if len(input_t) > 0:
            input_h = parser.render_input_text(head)
            for output, count in self.search(input_h).items():
                results[output + parser.render_text(tail)] = count

        return results

    def search(self, roman_text):
        return self._search(self.input_generalizer(roman_text))

    def _search(self, roman_text):
        # Fetch results from memory. The work flow of the following
        # comprehension is as followes:
        #   - Find all the elements having target roman text,
        #     newest first.
        #
        #   - Cut the above sequence upto 'concern size' length.
        #     This is done because we only want to do frequency
        #     analysis on most recent data.
        #
        #   - Count the converted bangla texts and order them
        #     according to their relative frequency.
        hist = Counter(
            [
                bt for rt, bt
                in reversed(self.session_history)
                if rt == roman_text
            ][:self.session_history_concern_size]
        )

        if hist:
            return hist

        # Fetch results from disk, as we didn't find them in memory.
        #---------------------------------------------------------------\
        if self.conn is None:
            return Counter()

        try:
            hist = Counter()

            with self.conn:
                result = self.conn.execute(
                    self.QUERY_SEARCH, {"roman_text": roman_text})

                for bangla_text, freq in result:
                    hist[bangla_text] = freq

            return hist

        except sqlite3.Error as e:
            logging.exception("Could not read history from disk.")
            return Counter()
        #----------------------------------------------------------------/

    QUERY_SAVE_NEW = """
    INSERT INTO history (bangla_text, roman_text, usecount)
    VALUES (:bangla_text, :roman_text, 1);
    """

    QUERY_UPDATE_OLD = """
    UPDATE history SET usecount = usecount + 1
    WHERE roman_text = :roman_text AND bangla_text = :bangla_text;
    """

    def _split_trailing_punctuations_from_text(self, text, puncs):
        split_at = len(text)
        for c in reversed(text):
            if c in puncs:
                split_at += -1
            else:
                break

        return text[:split_at], text[split_at:]

    def save_without_punctuation(self, parser, bangla_text):
        # Save with punctuation.
        self.save(parser.input_text, bangla_text)

        # Get punctuationless head from the input.
        inp_head, _ = self._split_trailing_punctuations_from_cord(
            parser.cord, parser.rule.punctuations)

        # Get punctuationless head from the output.
        outp_head, _ = self._split_trailing_punctuations_from_text(
            bangla_text, parser.rule.punctuations)

        # Save without punctuation.
        self.save(parser.render_input_text(inp_head), outp_head)

    def save(self, roman_text, bangla_text):
        return self._save(self.input_generalizer(roman_text), bangla_text)

    def _save(self, roman_text, bangla_text):
        # Save data to memory.
        self.session_history.append((roman_text, bangla_text))

        # Save data to disk.
        #-----------------------------------------------------------------\
        if self.conn is None:
            return

        try:
            with self.conn:
                values = {
                    "roman_text": roman_text,
                    "bangla_text": bangla_text}

                result = self.conn.execute(self.QUERY_UPDATE_OLD, values)
                if result.rowcount == 0:
                    self.conn.execute(self.QUERY_SAVE_NEW, values)

        except sqlite3.Error as e:
            logging.exception("Could not save history to disk.")
        #-----------------------------------------------------------------/
