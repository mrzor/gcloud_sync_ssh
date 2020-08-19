import difflib
import os
import unicodedata

from colored import fg, attr


# This modules provides side by side, colored diff.
#
#
# It was greatly inspired by what icdiff does.
# Actually, some of this code is icdiff's code _verbatim_, and the rest is very
# strongly inspired by it.
# I believe icdiff license applies to this module as a result, which is:
#
#     This code is usable under the same open terms as the rest of python.
#     Copyright (c) 2001-2020 Python Software Foundation; All Rights Reserved
#
# Functionally:
# - no line wrapping
# - no built-in ANSI coloring
# - no tab handling
# - no CRLF handling
# - flawed in many subtle ways. should be replaced by icdiff's make_table once its
#   updated on PyPY

_COLOR_MAPPING = {
    "add": {"fg": "green", "bold": True},
    "subtract": {"fg": "red", "bold": True},
    "change": {"fg": "yellow", "bold": True},
    "separator": {"fg": "blue"},
    "description": {"fg": "blue"},
    "meta": {"fg": "magenta"},
    "line-numbers": {"fg": "light_gray"},
}


def _color_codes(category):
    mapping = _COLOR_MAPPING[category]
    codes = fg(mapping["fg"])
    if mapping.get("bold", False):
        codes += attr("bold")
    return codes


_DIFFLIB_TO_ANSI = {
    '\0+': _color_codes("add"),
    '\0-': _color_codes("subtract"),
    '\0^': _color_codes("change"),
    '\1': attr(0),
    '\t': ' '
}


def _colored(text, category):
    return f"{_color_codes(category)}{text}{attr(0)}"


def _colorize(s):
    # return s.replace("+", "").replace("-", "")
    for search, replace in _DIFFLIB_TO_ANSI.items():
        s = s.replace(search, replace)
    return s


def _display_len(s):
    # Handle wide characters like Chinese.
    def width(c):
        if ((isinstance(c, type(u"")) and
             unicodedata.east_asian_width(c) == 'W')):
            return 2
        elif c == '\r':
            return 2
        return 1
    return sum(width(c) for c in s)


def _real_len(s):
    s_len = 0
    zero_len_chars = set(['\0', '\1'])
    post_zero_len_chars = set(['+', '-', '^'])
    in_esc = False
    prev = ' '

    for c in s:
        if c in zero_len_chars:
            prev = c
            continue

        if prev == "\x00" and c in post_zero_len_chars:
            prev = c
            continue

        if in_esc:
            if c == "m":
                in_esc = False
        else:
            if c == "[" and prev == "\033":
                in_esc = True
                s_len -= 1  # we counted prev when we shouldn't have
            else:
                s_len += _display_len(c)
            prev = c

    return s_len


def _pad(s, field_width):
    return " " * (field_width - _real_len(s))


def _lpad(s, field_width):
    return _pad(s, field_width) + s


def _rpad(s, field_width):
    return s + _pad(s, field_width)


def _make_table(fromdesc, todesc, diffs):
    if fromdesc or todesc:
        yield ("", _colored(fromdesc, "description"), _colored(todesc, "description"))

    for _from, _to, _flag in diffs:
        if _flag is None:
            sep = _colored("---", "separator")
            yield (sep, sep, sep)
        else:
            _line = _from[0]
            _from_s = _from[1] if _from[0] else ""
            _to_s = _to[1] if _to[0] else ""
            yield (_line, _from_s, _to_s)


def _add_line_numbers(linenum, text):
    try:
        lid = '%d' % linenum
    except TypeError:
        # handle blank lines where linenum is '>' or ''
        lid = ''
        return (" " * 7) + text
    return '%s %s' % (
        _lpad(_colored(str(lid), "line-numbers"), 6), text)


def terminal_width():
    if os.name == 'nt':
        try:
            import struct
            from ctypes import windll, create_string_buffer

            fh = windll.kernel32.GetStdHandle(-12)  # stderr is -12
            csbi = create_string_buffer(22)
            windll.kernel32.GetConsoleScreenBufferInfo(fh, csbi)
            res = struct.unpack("hhhhHhhhhhh", csbi.raw)
            return res[7] - res[5] + 1  # right - left + 1
        except Exception:
            return 80

    else:
        def ioctl_GWINSZ(fd):
            try:
                import fcntl
                import termios
                import struct
                cr = struct.unpack('hh', fcntl.ioctl(fd,
                                                     termios.TIOCGWINSZ,
                                                     '1234'))
            except Exception:
                return None
            return cr
        cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
        if cr and cr[1] > 0:
            return cr[1]
    return 80


def pretty_diff(a, b, cols=None, fromdesc='', todesc='', context_lines=3):
    cols = terminal_width() if not cols else cols
    half_col = (cols // 2) - 3 - 7  # 3 because of center ' | ', 7 because of line numbers

    a = [line.rstrip('\n') for line in a]
    b = [line.rstrip('\n') for line in b]
    table = _make_table(fromdesc, todesc, difflib._mdiff(a, b, context_lines))

    for linenum, left, right in table:
        text = _colorize(f"{_rpad(left, half_col)} | {_rpad(right, half_col)}")
        yield _add_line_numbers(linenum, text)
