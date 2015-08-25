import re


_ESCAPED_UNICHAR_REGEX = re.compile(r'\\u[0-9A-F]{4}', re.I)

def _unescape_unichar(text):
    def replace(matchobj):
        return chr(int(matchobj.group(0)[2:], 16))

    return re.sub(_ESCAPED_UNICHAR_REGEX, replace, text)


class Rule:
    def __init__(self, ruledir):
        self.ruledir = ruledir
        with open("avro_rule/transliterations.txt") as f:
            print(self._parse_transliterations(f.read()))
        with open("avro_rule/vowelmap_dist2diac.txt") as f:
            print(self._parse_vowelmap(f.read()))
        with open("avro_rule/vowelmap_diac2dist.txt") as f:
            print(self._parse_vowelmap(f.read()))
        with open("avro_rule/consonants.txt") as f:
            print(self._parse_consonants(f.read()))
        with open("avro_rule/vowelhosts.txt") as f:
            print(self._parse_vowelhosts(f.read()))
        with open("avro_rule/conjunction_glue.txt") as f:
            print("Halant is: {}".format(
                self._parse_conjunction_glue(f.read())))


    def _parse_conjunction_glue(self, text):
        return _unescape_unichar(''.join(filter(
            lambda x: not x.startswith('#'),
            map(str.strip, text.splitlines())
        ))).strip()



    def _parse_transliterations(self, text):
        transmap = {}

        for line in text.splitlines():
            line = line.strip()

            # Ignore empty lines.
            if not line:
                continue

            # Ignore comments.
            if line.startswith('#'):
                continue

            try:
                src, dst = line.split('#', maxsplit=1)
            except ValueError:
                src, dst = line, ''

            srcfrags = list(map(_unescape_unichar, src.split()))
            dstfrags = list(map(_unescape_unichar, dst.split()))

            for sf in srcfrags:
                transmap[sf] = dstfrags

        return transmap

    def _parse_vowelmap(self, text):
        vowelmap = {}

        for line in text.splitlines():
            line = line.strip()

            if not line:
                continue

            if line.startswith('#'):
                continue

            try:
                src, dst = line.split(maxsplit=1)
            except ValueError:
                src, dst = line, ''

            src = _unescape_unichar(src)
            dst = _unescape_unichar(dst)

            vowelmap[src] = dst

        return vowelmap

    def _parse_consonants(self, text):
        chars = set()

        for line in text.splitlines():
            line = line.strip()

            if not line:
                continue

            if line.startswith('#'):
                continue

            chars.update(map(_unescape_unichar, line.split()))

        return chars

    _parse_vowelhosts = _parse_consonants
    


r = Rule('cc')
