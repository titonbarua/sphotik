#!/usr/bin/env python3
import sys
import string
import os.path
import unicodedata
from pkgutil import get_data
from tempfile import NamedTemporaryFile

from gi.repository import IBus, GLib
from gi.repository.IBus import ModifierType as Mod

from sphotiklib.parser import Parser
from sphotiklib.ruleparser import Rule

from .parser import ParserIbus
from .history import HistoryManager


RULESET_NAME = "avro"

MAX_WORD_LENGTH = 40
ENCHANT_DICT_NAMES = ['bn_BD', 'bn']
HISTORY_FILE_PATH = "~/.sphotik_history.sqlite"

LOOKUP_TABLE_PAGE_SIZE = 5
LOOKUP_TABLE_ORIENTATION = 1  # 1 = vertical, 0 = horizontal
LOOKUP_TABLE_IS_ROUND = False


# Keys to look after. An example of uninteresting event is
# CTRL key press event ( note that this is seperate from
# CTRL + some other key press event ).
INTERESTING_KEYS = set([getattr(IBus, c) for c in (
    [
        "Escape",

        "space",
        "Return",
        "BackSpace",
        "Delete",
        "Tab",

        "asciitilde",
        "grave",

        "exclam",
        "at",
        "numbersign",
        "dollar",
        "percent",
        "asciicircum",
        "ampersand",
        "asterisk",
        "parenleft",
        "parenright",
        "minus",
        "underscore",
        "plus",
        "equal",

        "colon",
        "semicolon",
        "quotedbl",
        "apostrophe",

        "less",
        "comma",
        "greater",
        "period",
        "question",
        "slash",
        "backslash",

        "Left",
        "Right",
        "Up",
        "Down",

        "Page_Up",
        "Page_Down",
    ]
    + list(string.digits)
    + list(string.ascii_letters)
)])

# Ignore key release events.
STATES_TO_IGNORE = Mod.RELEASE_MASK

# Commit as soon as ALT/CTRL/SUPER modifiers are set.
# Pass the character unmodified as it is most probably
# an editor command.
STATES_TO_COMMIT_ASAP = (
    Mod.CONTROL_MASK
    | Mod.MOD1_MASK
    | Mod.SUPER_MASK
    | Mod.META_MASK
    | Mod.HYPER_MASK)


ENGINE_NAME = "sphotik"
ENGINE_BUS_NAME = "org.freedesktop.IBus.Sphotik"
COMPONENT_TEMPLATE = "sphotik.xml.tmpl"


def count_graphemes(text):
    """This is probably the most stupid grapheme counter ever,
    but hopefully it will be enough for our purpose.
    """
    return len([
        # Count all chars except unicode 'mark's.
        c for c in text if not unicodedata.category(c).startswith('M')])


class _UselessEnchantDict:

    def suggest(self, text):
        return []


class LookupTableManager:

    def __init__(self, *args, **kwargs):
        self._table = IBus.LookupTable(*args, **kwargs)
        self.clear()

    def clear(self):
        self._table.clear()
        self._finalized = False

        # Place to dump entries. Every entry is a tuple of
        # four elements: (type, freq, text, ibus_text)
        self._entries = []

        # Place to hold the entries at exact order matching
        # the underlaying lookup table.
        self._finalized_entries = []

        # Collection of all the texts ( 3rd element ) from
        # finalized entries.
        self._finalized_entry_texts = set()

    def add_entry(self, type_, freq, text, ibus_text=None):
        if ibus_text is None:
            ibus_text = IBus.Text.new_from_string(text)

        self._entries.append((type_, freq, text, ibus_text))
        self._finalized = False

    @property
    def table(self):
        if self._finalized:
            return self._table

        # Select all entries of type 'default'. They go to top
        # of the list, internally sorted by their freq.
        default_entries = list(sorted(
            [e for e in self._entries if e[0] == 'default'],
            key=lambda x: x[1],
            reverse=True))

        # Select all entries except 'default'. They are also
        # sorted according to their freq.
        other_entries = list(sorted(
            [e for e in self._entries if e[0] != 'default'],
            key=lambda x: x[1],
            reverse=True))

        # Sort entries by their frequency of appearence,
        # but always keep entries of type 'default' at top.
        sorted_entries = list(sorted(
            self._entries,
            key=lambda e: ((e[0] == 'default'), e[1]),
            reverse=True))

        # Finalize entries with unique 'text'.
        for i, e in enumerate(sorted_entries):
            type_, freq, text, ibus_text = e

            if text in self._finalized_entry_texts:
                continue

            self._finalized_entries.append(e)
            self._finalized_entry_texts.add(text)
            self._table.append_candidate(ibus_text)

        if self._entries:
            # Set the cursor to text with highest frequency.
            max_freq = max([e[1] for e in self._entries])
            for i, (_, freq, _, _) in enumerate(self._finalized_entries):
                # We are only concerned with the first candidate with
                # maximum frequency.
                if freq == max_freq:
                    self._table.set_cursor_pos(i)
                    break

        self._finalized = True
        return self._table

    def entry_exists(self, text):
        return text in self._finalized_entry_texts

    def get_entry(self, index):
        return self._finalized_entries[index]

    def get_entry_under_cursor(self):
        return self.get_entry(self._table.get_cursor_pos())

    def __len__(self):
        return len(self._finalized_entries)

    def cursor_up(self):
        self.table.cursor_up()

    def cursor_down(self):
        self.table.cursor_down()

    def page_up(self):
        self.table.page_up()

    def page_down(self):
        self.table.page_down()


class EngineSphotik(IBus.Engine):
    ruleset_name = RULESET_NAME

    max_word_length = MAX_WORD_LENGTH
    enchant_dict_names = ENCHANT_DICT_NAMES
    history_file_path = os.path.expanduser(HISTORY_FILE_PATH)

    lookup_table_page_size = LOOKUP_TABLE_PAGE_SIZE
    lookup_table_orientation = LOOKUP_TABLE_ORIENTATION
    lookup_table_is_round = LOOKUP_TABLE_IS_ROUND

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._rule = Rule(self.ruleset_name)
        self._parser = ParserIbus(self._rule)
        self._history_manager = HistoryManager(self.history_file_path)
        self._lookup_table_manager = LookupTableManager(
            self.lookup_table_page_size,
            0,  # Cursor index.
            True,  # Cursor is visible.
            self.lookup_table_is_round)

        self._lookup_table_manager.table.set_orientation(
            self.lookup_table_orientation)

        # Try to create an enchant dictionary from
        # any of the specified names. If all failed, create
        # a fake dictionary object that does nothing.
        for d in self.enchant_dict_names:
            try:
                import enchant

                try:
                    self._enchant_dict = enchant.Dict(d)
                    break
                except enchant.errors.DictNotFoundError:
                    pass
            except ImportError:
                self._enchant_dict = _UselessEnchantDict()
                print(
                    "[Warning] Failed to find enchant binding for python."
                    " Dictionary suggestions will not be available.")
                break
        else:
            self._enchant_dict = _UselessEnchantDict()
            print(
                "[Warning] Failed to find any Bangla dictionary."
                " Dictionary suggestions will not be available.")

    def _update_lookup_table(self, remake=True):
        ltm = self._lookup_table_manager
        default_text = self._parser.text

        # If not instructed to remake, don't.
        if not remake:
            self.update_lookup_table_fast(ltm.table, len(ltm) > 0)
            return

        ltm.clear()  # Clear lookup table.

        # No point in making a lookup table if we don't have
        # enough of transliterated text.
        if not len(default_text) > 0:
            self.update_lookup_table_fast(ltm.table, len(ltm) > 0)
            return

        # hist = self._history_manager.search(self._parser.input_text)
        hist = self._history_manager.search_without_punctuation(self._parser)

        # Add default text to suggestions.
        ltm.add_entry("default", hist[default_text], default_text)

        # Add simple suggestions made by flag modifications.
        for sug in self._parser.suggest_flag_modifications():
            ltm.add_entry("flagmod", hist[sug], sug)

        # Add dictionary suggestions.
        for sug in self._enchant_dict.suggest(default_text):
            ltm.add_entry("dict", hist[sug], sug)

        # Finalize the table.
        table = ltm.table

        # If parser-cursor is not residing at it's natural rightmost
        # position, table-cursor should sit on top of default text.
        if not self._parser.cursor >= len(self._parser.cord):
            table.set_cursor_pos(0)

        self.update_lookup_table_fast(ltm.table, len(ltm) > 0)

    def _update(self, remake_lookup_table=True):
        self._update_lookup_table(remake_lookup_table)

        # Update preedit text. If lookup table has the 'default'
        # text selected, then preedit text should be the special
        # one with the custom preedit cursor in it. Otherwise, we
        # show currently selected candidate as preedit text.
        #-------------------------------------------------------------------\
        try:
            type_, freq, text, itext = (
                self._lookup_table_manager.get_entry_under_cursor())

            if type_ == "default":
                itext = self._parser.preedit_itext

            self.update_preedit_text_with_mode(
                itext, itext.get_length(), True, IBus.PreeditFocusMode.CLEAR)

        except IndexError:
            self.hide_preedit_text()
        #-------------------------------------------------------------------/

        # Update auxiliary text.
        self.update_auxiliary_text(
            self._parser.auxiliary_itext, len(self._parser.cord) > 0)

        # Commit text if our cord length gets bigger than permissible limits.
        if len(self._parser.cord) > self.max_word_length:
            self._commit()
            self._update()

    def _commit_from_lookup_table(self):
        if not len(self._lookup_table_manager) > 0:
            return False

        type_, freq, text, itext = (
            self._lookup_table_manager.get_entry_under_cursor())

        # We don't want to commit 'default' texts from this function.
        if type_ == 'default':
            return False

        # Do commit.
        self.commit_text(itext)

        # Save history.
        self._history_manager.save_without_punctuation(
            self._parser, itext.get_text())

        # Clear parser.
        self._parser.clear()

        return True

    def _commit(self):
        if not self._commit_from_lookup_table():
            # Do commit.
            self.commit_text(self._parser.itext)

            # Save history.
            self._history_manager.save_without_punctuation(
                self._parser, self._parser.text)

            # Clear parser.
            self._parser.clear()

    def _commit_upto_cursor(self):
        if not self._commit_from_lookup_table():
            cursor = self._parser.cursor

            to_commit = self._parser.cord[:cursor]
            to_retain = self._parser.cord[cursor:]

            # Do commit.
            self.commit_text(self._parser._render_itext(to_commit))

            # Save history.
            self._history_manager.save_without_punctuation(
                self._parser, self._parser.render_text(to_commit))

            # Create new parser with uncommited text.
            self._parser = ParserIbus(self._rule, to_retain, 0)

    def _idle_update(self):
        """
        Run _update method when CPU is idle.

        When users type very fast, fetching suggestions for every key insert
        can incure significant runtime cost and sluggish user experience.
        This function prevents that by running the _update method only when
        the CPU is idle.
        """

        def updater(self):
            if self._outdated:
                self._outdated = False
                self._update()

        self._outdated = True
        GLib.idle_add(updater, self)

    def do_candidate_clicked(self, index, button, state):
        pass

    def do_enable(self):
        self._parser.clear()

    def do_disable(self):
        self._parser.clear()

    def do_focus_in(self):
        self._parser.clear()

    def do_focus_out(self):
        self._parser.clear()

    def do_process_key_event(self, keyval, keycode, state):
        if keyval not in INTERESTING_KEYS:
            return False

        elif state & STATES_TO_IGNORE:
            return False

        elif state & STATES_TO_COMMIT_ASAP:
            self._commit()
            self._update()
            return False

        elif keyval == IBus.space:
            keystr = IBus.keyval_to_unicode(keyval)
            self._parser.insert(keystr)
            self._commit_upto_cursor()
            self._update()
            return True

        elif keyval == IBus.Return:
            if len(self._parser.cord) > 0:
                self._commit_upto_cursor()
                self._update()
                # This is a work around for Skype on Linux v4.3.0.37.
                # Skype discards any CR char at the end of commit text.
                # But if a commit is made while the CR is left unhandled,
                # the CR appears before the committed text in the chatlog.
                # As a work around, we don't let skype handle the original
                # CR, commit current buffer and then generate an spurious CR.
                self.forward_key_event(keyval, keycode, state)
                return True
            else:
                return False

        elif keyval == IBus.Tab:
            if len(self._parser.cord) == 0:
                return False

            self._commit()
            self._update()
            return True

        elif keyval == IBus.BackSpace:
            if len(self._parser.cord) == 0:
                return False

            self._parser.delete(-1)
            self._idle_update()
            return True

        elif keyval == IBus.Delete:
            if self._parser.cursor >= len(self._parser.cord):
                return False

            self._parser.delete(1)
            self._idle_update()
            return True

        elif keyval == IBus.Left:
            if len(self._parser.cord) == 0:
                return False

            if self._parser.cursor == 0:
                # Commit the current text and update immediately.
                itext = self._parser.itext
                self.commit_text(itext)
                self._parser.clear()
                self._update()

                # Since our cursor is placed at right side of the committed
                # text, let's go back to previous position by going left by
                # the number of graphemes commited. Go an extra step back to
                # account for the actual key press.
                for x in range(count_graphemes(itext.get_text()) + 1):
                    self.forward_key_event(keyval, keycode, state)

                return True

            self._parser.normcursor += -1
            self._idle_update()
            return True

        elif keyval == IBus.Right:
            if len(self._parser.cord) == 0:
                return False

            self._parser.normcursor += 1
            self._idle_update()
            return True

        elif keyval == IBus.Up:
            if not len(self._lookup_table_manager) > 0:
                return False

            self._lookup_table_manager.cursor_up()
            self._update(remake_lookup_table=False)
            return True

        elif keyval == IBus.Down:
            if not len(self._lookup_table_manager) > 0:
                return False

            self._lookup_table_manager.cursor_down()
            self._update(remake_lookup_table=False)
            return True

        elif keyval == IBus.Page_Up:
            if not len(self._lookup_table_manager) > 0:
                return False

            self._lookup_table_manager.page_up()
            self._update(remake_lookup_table=False)
            return True

        elif keyval == IBus.Page_Down:
            if not len(self._lookup_table_manager) > 0:
                return False

            self._lookup_table_manager.page_down()
            self._update(remake_lookup_table=False)
            return True

        elif keyval == IBus.Escape:
            if not len(self._lookup_table_manager) > 0:
                return False

            # Put lookup table cursor to default position
            # if it is not already.
            table = self._lookup_table_manager.table
            if table.get_cursor_pos() > 0:
                table.set_cursor_pos(0)
                self._update(remake_lookup_table=False)
                return True

            # Discard preedit text.
            self._parser.clear()
            self._update()
            return True

        else:
            keystr = IBus.keyval_to_unicode(keyval)
            self._parser.insert(keystr)
            self._idle_update()

            return True


def render_component_template(version, run_path, setup_path, icon_path):
    component_xml = (
        get_data(__package__, COMPONENT_TEMPLATE)
        .decode()
        .format(
            sphotik_version=version,
            sphotik_exec_path=run_path,
            sphotik_setup_path=setup_path,
            sphotik_icon_path=icon_path,
        )
    )

    return component_xml


def main():
    mainloop = GLib.MainLoop()
    bus = IBus.Bus()

    def quit(*args, **kwargs):
        mainloop.quit()

    bus.connect("disconnected", quit)

    factory = IBus.Factory.new(bus.get_connection())
    factory.add_engine(ENGINE_NAME, EngineSphotik)

    if len(sys.argv) > 1 and sys.argv[1] == '--ibus':
        bus.request_name(ENGINE_BUS_NAME, 0)
    else:
        # Let us do the ridiculous procedure of rendering the xml template
        # file and then saving it's content to a temporary file, then pass
        # the filename to generate a new ibus component!
        #-------------------------------------------------------------------\
        version_file = os.path.join(
            os.path.dirname(__file__), "..", "VERSION.txt")
        with open(version_file) as f:
            version = f.read().strip()

        component_data = render_component_template(
            version, '{} --ibus'.format(os.path.realpath(sys.argv[0])), '', '')

        with NamedTemporaryFile() as f:
            f.write(component_data.encode())  # Write data to a file.
            f.seek(0)  # Rewind.
            bus.register_component(IBus.Component.new_from_file(f.name))
        #-------------------------------------------------------------------/
        bus.set_global_engine_async(ENGINE_NAME, -1, None, None, None)

    mainloop.run()

if __name__ == "__main__":
    sys.path.insert(0, '..')
    main()
