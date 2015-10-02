#!/usr/bin/env python3
import sys
import string
import os.path
import unicodedata
from pkgutil import get_data
from tempfile import NamedTemporaryFile

import enchant
from enchant.errors import DictNotFoundError
from gi.repository import IBus, GLib
from gi.repository.IBus import ModifierType as Mod

from sphotiklib.parser import Parser
from sphotiklib.ruleparser import Rule

from .parser import ParserIbus


# Keys to look after. An example of uninteresting event is
# CTRL key press event ( note that this is seperate from
# CTRL + some other key press event ).
INTERESTING_KEYS = set([getattr(IBus, c) for c in (
    [
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

        "Left",
        "Right",
        "Up",
        "Down",
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
        self.lt = IBus.LookupTable(*args, **kwargs)
        self.clear()

    def clear(self):
        self.lt.clear()

        # Every entry is a tuple of 3 elements: (type, text, ibus_text)
        self._entries = []

        # This set holds all the texts ( 2nd elem ) from self._entries.
        # This is to enture that all entries are unique.
        self._entry_texts = set()

    def add_entry(self, type_, text, ibus_text=None):
        if text in self._entry_texts:
            return

        if ibus_text is None:
            ibus_text = IBus.Text.new_from_string(text)

        self._entries.append((type_, text, ibus_text))
        self._entry_texts.add(text)

        self.lt.append_candidate(ibus_text)

    def get_entry(self, index):
        return self._entries[index]

    def get_entry_under_cursor(self):
        return self.get_entry(self.lt.get_cursor_pos())

    def __len__(self):
        return len(self._entries)

    def cursor_up(self):
        self.lt.cursor_up()

    def cursor_down(self):
        self.lt.cursor_down()

    def page_up(self):
        self.lt.page_up()

    def page_down(self):
        self.lt.page_down()


class EngineSphotik(IBus.Engine):
    max_word_length = 40
    enchant_dict_names = ['bn_BD', 'bn']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._parser = ParserIbus(Rule('avro'))
        self._lookup_table_manager = LookupTableManager(5, 0, True, True)

        # Try to create an enchant dictionary from
        # any of the specified names. If all failed, create
        # a fake dictionary object that does nothing.
        for d in self.enchant_dict_names:
            try:
                self._enchant_dict = enchant.Dict(d)
                break
            except DictNotFoundError:
                pass
        else:
            self._enchant_dict = _UselessEnchantDict()
            print(
                "[Warning] Failed to find any Bangla dictionary."
                " Dictionary suggestions will not be available.")

    def _update_lookup_table(self, remake=True):
        ltm = self._lookup_table_manager

        # If remake flag is false, we don't recreate the table.
        if remake:
            ltm.clear()

            default_text = self._parser.text
            if len(default_text) > 0:
                # Add default text to suggestions.
                ltm.add_entry("default", default_text)

                # Add dictionary suggestions.
                for sug in self._enchant_dict.suggest(default_text):
                    ltm.add_entry("dict", sug)

        self.update_lookup_table_fast(ltm.lt, len(ltm) > 0)

    def _update(self, remake_lookup_table=True):
        self._update_lookup_table(remake_lookup_table)

        # Update preedit text. If lookup table has the 'default'
        # text selected, then preedit text should be the special
        # one with the custom preedit cursor in it. Otherwise, we
        # show currently selected candidate as preedit text.
        #-------------------------------------------------------------------\
        try:
            type_, text, itext = (
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

        type_, text, itext = self._lookup_table_manager.get_entry_under_cursor(
        )
        if type_ == 'default':
            return False

        self.commit_text(itext)
        self._parser.clear()
        return True

    def _commit(self):
        if not self._commit_from_lookup_table():
            self.commit_text(self._parser.itext)
            self._parser.clear()

    def _commit_upto_cursor(self):
        if not self._commit_from_lookup_table():
            cursor = self._parser.cursor

            to_commit = self._parser.cord[:cursor]
            self.commit_text(self._parser._render_itext(to_commit))

            to_retain = self._parser.cord[cursor:]
            self._parser = ParserIbus(self._parser.rule, to_retain, 0)

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

        if state & STATES_TO_IGNORE:
            return False

        if state & STATES_TO_COMMIT_ASAP:
            self._commit()
            self._update()
            return False

        if keyval in (IBus.space, IBus.Return):
            self._commit_upto_cursor()
            self._update()
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
