import pytest
from subprocess import CalledProcessError

from gcloud_sync_ssh.util.cmd import cmd


def test_args_as_string():
    r = cmd("echo -n 1 2 3")
    assert r.stdout == "1 2 3"


def test_args_as_array():
    r = cmd(["echo", "-n", "1", "2", "3"])
    assert r.stdout == "1 2 3"


def test_log_args(caplog):
    cmd("echo 1 2 3")
    assert len(caplog.records) == 1
    assert "echo 1 2 3" in caplog.text


def test_log_disabling(caplog):
    cmd("echo 1 2 3", debuglog=False)
    assert len(caplog.records) == 0


def test_log_errors_with_pipe(caplog):
    with pytest.raises(CalledProcessError) as e:
        cmd(["bash", "-c", "echo $((21 * 2)) >&2; exit 40"])
    assert len(caplog.records) == 2
    assert "status 40" in str(e.value)
    assert caplog.records[1].levelname == "ERROR"
    assert "42" in caplog.records[1].message  # make sure stderr is logged


def test_log_errors_without_pipe(caplog):
    with pytest.raises(CalledProcessError) as e:
        cmd(["bash", "-c", "echo $((21 * 2)) >&2; exit 40"], pipe=False)
    assert len(caplog.records) == 2
    assert "status 40" in str(e.value)
    assert caplog.records[1].levelname == "ERROR"
    assert "42" not in caplog.records[1].message  # make sure stderr is _not_ logged


def test_no_check(caplog):
    r = cmd(["bash", "-c", "echo $((21 * 2)) >&2; exit 40"], check=False, debuglog=False)
    assert len(caplog.records) == 0
    assert r.returncode == 40


def test_structured():
    # Use a bash subprocess to swallow the --format=json argument thanks to --
    r = cmd(["bash", "-c", 'echo "{\\"json-k\\": \\"json-v\\"}"', "--"], structured=True)
    assert "json-k" in r
    assert r["json-k"] == "json-v"


def test_pipe(capfd):
    # Bash used for stream redirections
    r = cmd(["bash", "-c", "echo out; echo err >&2"], pipe=True)
    assert r.returncode == 0

    outerr = capfd.readouterr()
    assert outerr.out == ""
    assert outerr.err == ""
    assert r.stdout == "out\n"
    assert r.stderr == "err\n"


def test_no_pipe(capfd):
    # Bash used for stream redirections
    r = cmd(["bash", "-c", "echo out; echo err >&2"], pipe=False)
    assert r.returncode == 0

    outerr = capfd.readouterr()
    assert outerr.out == "out\n"
    assert outerr.err == "err\n"
