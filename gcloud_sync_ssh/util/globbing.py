from fnmatch import fnmatch
import re


def matches_any(string, globs=[]):
    """Returns True when STRING matches any of the patterns given in GLOBS.

       Matching is done following the rules of fnmatch, see:
       https://docs.python.org/3.6/library/fnmatch.html#module-fnmatch

       Special case: if GLOBS is None or empty, then return True."""
    if globs is None:
        return True

    if len(globs) == 0:
        return True

    for glob in globs:
        if fnmatch(string, glob):
            return True
    return False


_RE_LOOKS_LIKE_GLOB = re.compile(r"[?*\[\]]")


def looks_like_pattern(string):
    """Returns True when STRING contains a '?', a '*' or '[]' and thus could
       be reasonably believed to be a fnmatch style pattern ('glob')."""
    if _RE_LOOKS_LIKE_GLOB.search(string):
        return True
    return False


def has_pattern(str_or_strlist):
    """When passed a string, equivalent to calling looks_like_pattern.
       When passed a string list, returns True if any one of the strings looks like a pattern,
       False otherwise."""
    strlist = [str_or_strlist] if isinstance(str_or_strlist, str) else str_or_strlist
    return len([s for s in strlist if looks_like_pattern(s)]) > 0
