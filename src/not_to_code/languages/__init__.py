"""One module per analyzed language, each with the same five functions.

read_tokens(a, adapter) and read_structure(a, adapter) fill an Analysis in place.
read_string(text), is_filesystem_call(tokens, i, lines) and
is_directory_change(tokens, i) answer the path and working-directory rules.
"""

from . import python, r, stata

LANGUAGES = {"python": python, "r": r, "stata": stata}
