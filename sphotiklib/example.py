#!/usr/bin/env python3
# This file shows usage of the Parser class in sphotiklib package.
import sys
import os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sphotiklib.parser import Parser
from sphotiklib.ruleparser import Rule

# We will use the builtin ruleset 'avro'.
p = Parser(Rule('avro'))

# Input made as a big string.
p.insert('kichu manuSh sbadhInvabe soman morzada')

# Input made in small-chunks.
for c in ' ebong odhikar niye jonmogrohon kore.':
    p.insert(c)

# Print parsed text.
print(p.text)

# cursor attribute can be used to insert chars at arbitrary positions.
# Cursor is only meaningful in converted text domain.
p.cursor = 5

# delete method can be used to delete text at cursor. Positive step means
# deletion from front. Negative means deletion from back.
p.delete(-5)
print(p.text)

p.insert('somosto ')
print(p.text)
