from click.testing import CliRunner

from gcloud_sync_ssh.cli import cli


def test_help():
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0


# XXX need to setup some form of DI to test gcloud without IPC
#     ... or not. just prepend a test "gcloud" in PATH for testing : problem solved.
