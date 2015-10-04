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
            output_sanitizer=lambda x: x,
            session_history_size=1000,
            session_history_concern_size=20,):
        # An input generalizer is a function that may be used to
        # generalize the input data, so that history suggestions can be
        # laxed and fuzzy; trading their accuracy in return.
        self.input_generalizer = input_generalizer

        # Output sanitizer is used to sanitize suggestion data.
        # As history is read from a sqlite file, it it unreliable and maybe
        # used with malicious intent. But defining the sanitizer function
        # remains a challenge. # TODO
        self.output_sanitizer = output_sanitizer

        # Session history is an in-memory sequence of most recently used
        # words and their input texts. The most likely conversion of a word
        # can be deduced by filtering the sequence by respective input text
        # and doing a frequency analysis on the used output texts.
        self.session_history_concern_size = session_history_concern_size
        self.session_history = deque(maxlen=session_history_size)

        if not os.path.isfile(histfilepath):
            # Create database it it does not exist.
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

    def search(self, roman_text):
        return self.output_sanitizer(
            self._search(self.input_generalizer(roman_text)))

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
        bangla_texts = [
            text for text, count in Counter(
                [
                    bt for rt, bt
                    in reversed(self.session_history)
                    if rt == roman_text
                ][:self.session_history_concern_size]
            ).most_common()
        ]

        if bangla_texts:
            return bangla_texts

        # Fetch results from disk, as we didn't find them in memory.
        #---------------------------------------------------------------\
        if self.conn is None:
            return []

        try:
            bangla_texts = []

            with self.conn:
                result = self.conn.execute(
                    self.QUERY_SEARCH, {"roman_text": roman_text})

                for bangla_text, _ in result:
                    bangla_texts.append(bangla_text)

            return bangla_texts

        except sqlite3.Error as e:
            logging.exception("Could not read history from disk.")
            return []
        #----------------------------------------------------------------/

    QUERY_SAVE_NEW = """
    INSERT INTO history (bangla_text, roman_text, usecount)
    VALUES (:bangla_text, :roman_text, 1);
    """

    QUERY_UPDATE_OLD = """
    UPDATE history SET usecount = usecount + 1
    WHERE roman_text = :roman_text AND bangla_text = :bangla_text;
    """

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
