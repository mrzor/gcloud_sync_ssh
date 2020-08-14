import pytest

from gcloud_sync_ssh.util.cased_enum import UppercaseStringEnum, LowercaseStringEnum


def test_lowercase_enum():
    class _TestLowercaseStringEnum(LowercaseStringEnum):
        bbb = "bbb"
        ccc = "ccc"

    assert _TestLowercaseStringEnum("ccc") == "ccc"
    assert _TestLowercaseStringEnum("CCC") == "ccc"


def test_lowercase_enum_invalid_name():
    with pytest.raises(NameError):
        class _TestLowercaseStringEnum(LowercaseStringEnum):
            bBB = "bbb"
            ccc = "ccc"


def test_lowercase_enum_invalid_value():
    with pytest.raises(ValueError):
        class _TestLowercaseStringEnum(LowercaseStringEnum):
            bbb = "bBB"
            ccc = "ccc"


def test_uppercase_enum():
    class _TestUppercaseStringEnum(UppercaseStringEnum):
        BBB = "BBB"
        CCC = "CCC"

    assert _TestUppercaseStringEnum("ccc") == "CCC"
    assert _TestUppercaseStringEnum("CCC") == "CCC"


def test_uppercase_enum_invalid_name():
    with pytest.raises(NameError):
        class _TestUppercaseStringEnum(UppercaseStringEnum):
            bBB = "BBB"
            CCC = "CCC"


def test_uppercase_enum_invalid_value():
    with pytest.raises(ValueError):
        class _TestUppercaseStringEnum(UppercaseStringEnum):
            BBB = "bBB"
            CCC = "CCC"
