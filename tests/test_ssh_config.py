import os
import pytest
import re
import stat
from tempfile import NamedTemporaryFile, TemporaryDirectory

from gcloud_sync_ssh.ssh_config import SSHConfig, SSHConfigParseError, \
    _GCSS_COMMENT, _BEGIN_MARKER, _END_MARKER

from gcloud_sync_ssh.host_config import HostConfig, StrictHostKeyCheckingParam

_GCSS_LINECOUNT = _GCSS_COMMENT.count("\n") + 1
_RE_ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def _test_file_path(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "configfiles", filename)


def test_empty_file_appends_markers():
    with NamedTemporaryFile(mode="r", encoding="UTF-8") as f:
        conf = SSHConfig(f.name)
        assert conf.dirty
        conf.save()
        assert not conf.dirty

        f.seek(0)
        lines = f.readlines()
        assert len(lines) == 3 + _GCSS_LINECOUNT
        assert lines[1].startswith(_BEGIN_MARKER)
        assert lines[-1].startswith(_END_MARKER)


def test_config_file_load_1():
    with open(_test_file_path("exhibit_1"), "r") as f:
        lines = f.readlines()
        conf = SSHConfig(f.name)

    assert len(conf._lines) == len(lines)
    assert len(conf._hosts) == 2
    assert 'test-a.us-central1-b.project-name-1' in conf._hosts
    assert 'test-b.europe-west4-b.project-name-2' in conf._hosts
    assert 'defined_before_block' not in conf._hosts
    assert 'defined_after_block' not in conf._hosts

    assert not conf.dirty
    assert not conf.diff()


def test_config_file_load_2():
    with open(_test_file_path("exhibit_2"), "r") as f:
        lines = f.readlines()
        conf = SSHConfig(f.name)
    assert len(conf._lines) == len(lines)
    assert len(conf._hosts) == 1
    assert "test_host" in conf._hosts

    assert not conf.dirty
    assert not conf.diff()


def test_update_host_and_diff():
    conf = SSHConfig(_test_file_path("exhibit_1"))
    conf.update_host('test-a.us-central1-b.project-name-1', ip="4.4.4.4", id=None)
    diff = "\n".join(conf.diff())
    diff = _RE_ANSI_ESCAPE.sub('', diff)
    assert "1.11.11" in diff  # old ip
    assert "4.4.4.4" in diff


def test_update_host_noop():
    conf = SSHConfig(_test_file_path("exhibit_1"))
    conf.update_host('test-a.us-central1-b.project-name-1', ip="34.1.11.111", id=None)
    assert not conf.dirty


def test_no_end_marker():
    with pytest.raises(SSHConfigParseError) as e:
        SSHConfig(_test_file_path("broken_1"))
    assert "Mismatched markers" in str(e.value)


def test_no_begin_marker():
    with pytest.raises(SSHConfigParseError) as e:
        SSHConfig(_test_file_path("broken_2"))
    assert "Mismatched markers" in str(e.value)


def test_no_duplicated_begin_marker():
    with pytest.raises(SSHConfigParseError) as e:
        SSHConfig(_test_file_path("broken_4"))
    assert "Duplicate start marker" in str(e.value)


def test_unmatched_line(caplog):
    SSHConfig(_test_file_path("broken_3"))
    assert len(caplog.records) == 3
    assert [x.message for x in caplog.records] == \
        ["Can't match line #1: Single_keyword_directive_are_not_supported\n",
         'Keyword `Broken` assignment outside of Host block at line 2',
         'Keyword `Port` assignment outside of Host block at line 3']


def test_backup():
    small_test_data = "Host a\n  Port 1222"
    with TemporaryDirectory() as d:
        conf_path = os.path.join(d, "test")
        with open(conf_path, "w", encoding="UTF-8") as f:
            f.write(small_test_data)
            f.close()
        os.chmod(conf_path, stat.S_IRUSR | stat.S_IWUSR)

        conf = SSHConfig(conf_path)
        conf.backup()

        tmp_dir_files = os.listdir(d)
        backup_files = [fn for fn in tmp_dir_files if ("backup" in fn)]
        assert(len(backup_files) == 1)  # Backup should only create one file
        backup_file = os.path.join(d, backup_files[0])

        with open(backup_file, "r", encoding="UTF-8") as f:
            assert f.read() == small_test_data  # Backup should preserve contents
        backup_stat = os.stat(backup_file)
        assert stat.filemode(backup_stat.st_mode) == "-rw-------"  # Backup should preserve mode


def test_backup_no_overwrite():
    with TemporaryDirectory() as d:
        conf_path = os.path.join(d, "test")
        with open(conf_path, "w") as f:
            f.write("")
            f.close()
        with open(f"{conf_path}.backup.test-tag", "w") as f:
            f.write("")
            f.close()
        with pytest.raises(RuntimeError) as e:
            SSHConfig(conf_path).backup(tag="test-tag")
        assert "file exists" in str(e.value)


def test_infer_host_config():
    conf = SSHConfig(_test_file_path("exhibit_3"))
    hc = conf.infer_host_config()

    assert hc.minidict() == {'IdentitiesOnly': True,
                             'IdentityFile': '/stuff/_engine',
                             'StrictHostKeyChecking': StrictHostKeyCheckingParam.no,
                             'UserKnownHostsFile': '/stuff/_known_hosts'}


def test_infer_host_config_empty():
    with NamedTemporaryFile(mode="r", encoding="UTF-8") as f:
        conf = SSHConfig(f.name)
        assert conf.infer_host_config().minidict() == {}


def test_append_host_in_empty_file():
    with NamedTemporaryFile(mode="r", encoding="UTF-8") as f:
        conf = SSHConfig(f.name)
        assert conf.dirty  # should have markers
#        import pdb; pdb.set_trace()
        conf.update_host("new_host", "30.30.30.30", "1234321", HostConfig.default_config())

        assert conf._lines == ['\n',
                               f'{_BEGIN_MARKER}\n',
                               f'{_GCSS_COMMENT}\n',
                               '\n',
                               'Host new_host\n',
                               '    HostName 30.30.30.30\n',
                               '    IdentityFile /home/zor/.ssh/google_compute_engine\n',
                               '    UserKnownHostsFile /home/zor/.ssh/google_compute_known_hosts\n',
                               '    HostKeyAlias compute.1234321\n',
                               '    IdentitiesOnly yes\n',
                               '    CheckHostIP no\n',
                               f'{_END_MARKER}\n']


def test_append_host_using_defaults():
    conf = SSHConfig(_test_file_path("exhibit_4"))
    assert not conf.dirty
    conf.update_host("new_host", "30.30.30.30", "1234321", HostConfig.default_config())
    assert conf.dirty
    assert conf._lines == [f'{_BEGIN_MARKER}\n',
                           '\n',
                           'Host new_host\n',
                           '    HostName 30.30.30.30\n',
                           '    IdentityFile /home/zor/.ssh/google_compute_engine\n',
                           '    UserKnownHostsFile /home/zor/.ssh/google_compute_known_hosts\n',
                           '    HostKeyAlias compute.1234321\n',
                           '    IdentitiesOnly yes\n',
                           '    CheckHostIP no\n',
                           f'{_END_MARKER}\n',
                           '\n']


def test_remove_host_that_isnt_there():
    conf = SSHConfig(_test_file_path("exhibit_3"))
    assert not conf.remove_host("test_host_not_there")


def test_remove_host():
    conf = SSHConfig(_test_file_path("exhibit_3"))

    # Assert idempotent on removing non-configured host
    conf.remove_host("this_host_does_not_exist")
    assert not conf.dirty

    # Assert actual removal
    offset = conf.remove_host("test_host_b")
    assert offset > 0
    assert conf.dirty

    # Assert internal structures are correct after actual removal
    assert 'test_host_a' in conf._hosts
    assert 'test_host_b' not in conf._hosts
    assert 'test_host_c' in conf._hosts

    # Remove remaining two hosts and assert we're left with only marker comments
    # in conf._lines
    conf.remove_host("test_host_a")
    conf.remove_host("test_host_c")
    assert conf._lines == [f'{_BEGIN_MARKER}\n', f"{_END_MARKER}\n", "\n"]


# XXX add a test and an exhibit to test behavior around comments inside the fenced block


def test_hosts_of_project():
    conf = SSHConfig(_test_file_path("exhibit_1"))
    result = conf.hosts_of_project("project-name-1")
    assert len(result) == 1
    assert result['test-a.us-central1-b.project-name-1']

    result = conf.hosts_of_project("project-name-2")
    assert len(result) == 1
    assert result['test-b.europe-west4-b.project-name-2']
