import pytest
from gcloud_sync_ssh.util.case_insensitive_dict import CaseInsensitiveDict


def test_init():
    CaseInsensitiveDict()
    CaseInsensitiveDict({})
    CaseInsensitiveDict({1: 1})
    CaseInsensitiveDict(a=1, b=2)
    CaseInsensitiveDict([['a', 1], ['b', 2]])
    CaseInsensitiveDict.fromkeys(['a', 'b'])


def test_comp():
    da = {"aaa": 1000, "bbb": 3000, "ccc": 2000}
    d1 = CaseInsensitiveDict(da)
    assert(da == d1)

    db = [["aaa", 1000], ["bbb", 3000], ["ccc", 2000]]
    d2 = CaseInsensitiveDict(db)
    assert(d1 == d2)


@pytest.mark.skip(reason="pending / not implemented")
def test_eq():
    pass
    # XXX not implemented
    # assert(d2 == {"AAA": 1000, "BBB": 3000, "CCC": 2000})


def test_get():
    d = CaseInsensitiveDict({"aaa": 10, "bbb": 20})
    assert(d["aaa"] == 10)
    assert(d["aAa"] == 10)
    assert(d["AAa"] == 10)
    assert(d["aaA"] == 10)
    assert(d["BBB"] == 20)


def test_set():
    d = CaseInsensitiveDict(xoxo=1, yey=2, zaz=3)
    d['XOXO'] = 10
    d['yEY'] = 20
    assert(d == {'xoxo': 10, 'yey': 20, 'zaz': 3})


def test_del():
    d = CaseInsensitiveDict(xoxo=1, yey=2, zaz=3)
    del d['xoxo']
    assert d == {'yey': 2, 'zaz': 3}


def test_set_and_get():
    d = CaseInsensitiveDict()
    d[1] = 1000
    assert(d[1] == 1000)


def test_case_insensitive_set_and_get():
    d = CaseInsensitiveDict()
    d["abcdef"] = 1000
    assert(d["abcdef"] == 1000)
    assert(d["aBcDeF"] == 1000)
    assert(d["ABCDEF"] == 1000)


def test_case_insensitive_contains():
    d = CaseInsensitiveDict()
    d["abcdef"] = 1000
    assert("abcdef" in d)
    assert("aBcDeF" in d)
    assert("ABCDEF" in d)
    assert("ABZORF" not in d)


def test_case_insensitive_get():
    d = CaseInsensitiveDict()
    d["abcdef"] = 1000
    assert(d.get("abcdef") == 1000)
    assert(d.get("aBcDeF") == 1000)
    assert(d.get("ABCDEF") == 1000)
    assert(not d.get("ABZORF", None))


def test_case_insensitive_pop():
    d = CaseInsensitiveDict()

    d["abcdef"] = 1000
    assert(d.pop("abcdef") == 1000)
    assert("abcdef" not in d)

    d["abcdef"] = 1000
    assert(d.pop("aBcDeF") == 1000)
    assert("abcdef" not in d)
    assert("AbCdEf" not in d)

    d["abcdef"] = 1000
    assert(d.pop("ABCDEF") == 1000)
    assert("abcdef" not in d)
    assert("aBcDeF" not in d)
    assert("ABCDEF" not in d)


def test_pop_with_default():
    d = CaseInsensitiveDict()
    assert d.pop("oops", 10) == 10


def test_update():
    d = CaseInsensitiveDict()

    d.update({"xxx": 4, "yyy": 2})
    assert(d == {"xxx": 4, "yyy": 2})
    assert(d["XxX"] == 4)
    assert[d["YYY"] == 2]
    d.update(xXX=5, yYY=1)
    assert(d == {"xxx": 5, "yyy": 1})
    d.update(xXX=None, yYY=1000, ZZZ=0)
    assert(d == {"xxx": None, "yyy": 1000, "ZZZ": 0})


def test_popitem():
    d = CaseInsensitiveDict({1: 1000})
    i = d.popitem()
    assert i == (1, 1000)
    assert not d


def test_setdefault():
    d = CaseInsensitiveDict({1: 1000})
    d.setdefault(1, 10)
    d.setdefault(2, 2000)
    assert d[1] == 1000
    assert d[2] == 2000


def test_rekey():
    d = CaseInsensitiveDict({"aBa": 10})
    d.rekey("ABA")
    assert d == {"ABA": 10}
