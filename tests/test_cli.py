import json
import os
import re

from click.testing import CliRunner

from gcloud_sync_ssh.cli import cli

###############################################################################
#
# Helpers only relevant to this file
#
###############################################################################


def prep_simple_ctx(stubbed_gcloud_ctx,
                    sshconfig="exhibit_4",
                    project="stub-project-1", projects="projects_1",
                    instances="instances_1"):
    with stubbed_gcloud_ctx.db("config") as db:
        db.update({"project": project})
    stubbed_gcloud_ctx.seed_db("projects", projects)
    stubbed_gcloud_ctx.seed_db("instances", instances)
    return stubbed_gcloud_ctx.seed_configfile("ssh_config", sshconfig)


def assert_backup(original_path, caplog):
    backup_log_line = [line for line in caplog.messages if "config backed up to" in line][0]
    backup_path = backup_log_line[backup_log_line.index("/"):]
    assert os.path.exists(backup_path)

    with open(backup_path, "r") as f:
        backup_contents = f.read()

    with open(original_path, "r") as f:
        expected_contents = f.read()

    assert backup_contents == expected_contents


###############################################################################
#
# Tests for special subcommands and short-circuits
#
###############################################################################


def test_help():
    result = CliRunner().invoke(cli, ['--help'])
    assert result.exit_code == 0


def test_version(caplog):
    result = CliRunner().invoke(cli, ['--version'])
    assert result.exit_code == 0
    assert len(caplog.records) == 1
    version_string = caplog.records[0].message.split(" ")[1]

    def is_canonical(version):
        # https://www.python.org/dev/peps/pep-0440/#appendix-b-parsing-version-strings-with-regular-expressions
        return re.match(r'^([1-9][0-9]*!)?(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*'
                        r'((a|b|rc)(0|[1-9][0-9]*))?(\.post(0|[1-9][0-9]*))?'
                        r'(\.dev(0|[1-9][0-9]*))?$', version) is not None

    assert is_canonical(version_string)


###############################################################################
#
# Tests about host configuration template
#
###############################################################################


def test_debug_template_1(caplog, stubbed_gcloud_ctx):
    # This covers default behavior, with built-in defaults and inference
    config_path = prep_simple_ctx(stubbed_gcloud_ctx, sshconfig="exhibit_3")
    result = CliRunner().invoke(cli, ["--ssh-config", config_path, "--debug-template"])
    assert result.exit_code == 0
    template_lines = [line for line in result.stdout.split("\n") if "| INFO" not in line]
    assert len(template_lines) == 7


def test_debug_template_2(caplog, stubbed_gcloud_ctx):
    # This covers basic, empty host template
    config_path = prep_simple_ctx(stubbed_gcloud_ctx)
    result = CliRunner().invoke(cli, ["--ssh-config", config_path,
                                      "--debug-template", "--no-host-defaults", "--no-inference"])
    assert result.exit_code == 0
    template_lines = [line for line in result.stdout.split("\n") if line and "| INFO" not in line]
    assert len(template_lines) == 0


def test_debug_template_3(caplog, stubbed_gcloud_ctx):
    # This covers kwarg assignment
    config_path = prep_simple_ctx(stubbed_gcloud_ctx)
    result = CliRunner().invoke(cli, ["--ssh-config", config_path,
                                      "--debug-template", "--no-host-defaults", "--no-inference",
                                      "-kw", "IdentityAgent=None",
                                      "-kw", "HostbasedKeyTypes=who-knows-tbh",
                                      "-kw", "IdentityAgent=Thanatos"])
    assert result.exit_code == 0
    template_lines = [line for line in result.stdout.split("\n") if line and "| INFO" not in line]
    assert len(template_lines) == 2
    assert '    IdentityAgent Thanatos' in template_lines  # latest assignment has precedence


def test_debug_template_4(caplog, stubbed_gcloud_ctx):
    # This covers removing a builtin kwarg assignment
    config_path = prep_simple_ctx(stubbed_gcloud_ctx)
    result = CliRunner().invoke(cli, ["--ssh-config", config_path, "--debug-template",
                                      "--no-inference",
                                      "-kw", "CheckHostIP="])
    assert result.exit_code == 0
    template_lines = [line for line in result.stdout.split("\n") if line and "| INFO" not in line]
    assert len(template_lines) == 3
    assert len([line for line in template_lines if "CheckHostIP" in line]) == 0


def test_debug_template_5(caplog, stubbed_gcloud_ctx):
    # This covers using the same kwarg multiple times when SSH allows multiple values
    config_path = prep_simple_ctx(stubbed_gcloud_ctx)
    result = CliRunner().invoke(cli, ["--ssh-config", config_path, "--debug-template",
                                      "--no-inference", "no--host-defaults",
                                      "-kw", "DynamicForward=df1",
                                      "-kw", "DynamicForward=df2",
                                      "-kw", "LocalForward=lf1",
                                      "-kw", "DynamicForward=df3"])
    assert result.exit_code == 0
    template_lines = [line for line in result.stdout.split("\n") if line and "| INFO" not in line]
    assert len(template_lines) == 8
    assert len([line for line in template_lines if "DynamicForward" in line]) == 3
    assert len([line for line in template_lines if "LocalForward" in line]) == 1


def test_debug_template_6(caplog, stubbed_gcloud_ctx):
    # This covers using a case insensitive kwarg
    config_path = prep_simple_ctx(stubbed_gcloud_ctx)
    result = CliRunner().invoke(cli, ["--ssh-config", config_path, "--debug-template",
                                      "--no-inference",
                                      "-kw", "checkHostIp=yes"])
    assert result.exit_code == 0
    template_lines = [line for line in result.stdout.split("\n") if line and "| INFO" not in line]
    assert len(template_lines) == 4
    assert len([line for line in template_lines if "CheckHostIP" in line]) == 1


###############################################################################
#
# Tests for abnormal operation
#
###############################################################################


def test_invalid_invocation_1(caplog):
    result = CliRunner().invoke(cli, ["--project", "ah", "--all-projects"])
    assert result.exit_code == 1
    assert "cannot be used simultaneously" in result.stdout


def test_invalid_invocation_2(caplog, stubbed_gcloud_ctx):
    result = CliRunner().invoke(cli, [])
    assert result.exit_code == 1
    assert "could not determine an active project" in result.stdout


def test_invalid_invocation_3(caplog, stubbed_gcloud_ctx):
    result = CliRunner().invoke(cli, ["--login", "x", "--service-account", "y"])
    assert result.exit_code == 1
    assert "cannot be used simultaneously" in result.stdout


def test_invalid_invocation_4(caplog, stubbed_gcloud_ctx):
    result = CliRunner().invoke(cli, ["-kw", "no equals in this"])
    assert result.exit_code == 1
    assert "Invalid KWArg" in result.stdout


def test_invalid_invocation_5(caplog, stubbed_gcloud_ctx):
    result = CliRunner().invoke(cli, ["-kw", "thiswillneverbesupported=yes"])
    assert result.exit_code == 1
    assert "is not supported" in result.stdout


def test_invalid_invocation_6(caplog, stubbed_gcloud_ctx):
    result = CliRunner().invoke(cli, ["-kw", "ConnectionAttempts=oops"])
    assert result.exit_code == 1
    assert "is not a valid integer" in result.stdout


def test_invalid_ssh_config(caplog, stubbed_gcloud_ctx):
    config_path = stubbed_gcloud_ctx.seed_configfile("ssh_config", "broken_1")
    result = CliRunner().invoke(cli, ["--ssh-config", config_path])
    assert "parse error" in result.stdout
    assert "parse error" in "\n".join(caplog.messages)
    assert result.exit_code == 1


###############################################################################
#
# Tests for normal operation
#
###############################################################################

def assert_simple_run_I1(caplog, stubbed_gcloud_ctx, result):
    # This covers runs that use instances_1 stub
    assert result.exit_code == 0

    # Assert expected logs
    all_messages = "\n".join(caplog.messages)
    assert "1 projects" in all_messages
    assert "config backed up" in all_messages
    assert "Rewrote SSH config" in all_messages
    assert "stub-project-1" in all_messages

    # Asserts on outputted SSH config
    with stubbed_gcloud_ctx.tmpfile("ssh_config", mode="rt") as f:
        conflines = f.readlines()
        assert len([line for line in conflines if "Host " in line]) == 1
        assert len([line for line in conflines if "127.127.127.3" in line]) == 1

    # Asserts on backed up SSH config
    assert_backup(stubbed_gcloud_ctx.config_path("exhibit_4"), caplog)


def assert_simple_run_I2(caplog, stubbed_gcloud_ctx, result):
    # This covers runs that use instances_2 stub with all projects selected
    assert result.exit_code == 0

    # Assert expected logs
    all_messages = "\n".join(caplog.messages)
    expectations = ["3 projects", "config backed up", "Rewrote SSH config",
                    "stub-project-1", "stub-project-2", "stub-project-3",
                    "No instances in project stub-project-3",
                    "1 RUNNING, 1 TERMINATED"]
    for thing in expectations:
        assert thing in all_messages

    # Asserts on outputted SSH config
    with stubbed_gcloud_ctx.tmpfile("ssh_config", mode="rt") as f:
        conflines = f.readlines()
        assert len([line for line in conflines if "Host " in line]) == 2
        assert len([line for line in conflines if "127.127.127.3" in line]) == 1
        assert len([line for line in conflines if "127.127.127.6" in line]) == 1

    # Asserts on backed up SSH config
    assert_backup(stubbed_gcloud_ctx.config_path("exhibit_4"), caplog)


def test_simple_run_1(caplog, stubbed_gcloud_ctx):
    """Single project - empty configuration passed - not interactive"""
    config_path = prep_simple_ctx(stubbed_gcloud_ctx)
    result = CliRunner().invoke(cli, ["--ssh-config", config_path, "--not-interactive"])
    assert len([m for m in caplog.messages if "cmd" in m]) == 2
    assert_simple_run_I1(caplog, stubbed_gcloud_ctx, result)


def test_simple_run_2(caplog, stubbed_gcloud_ctx):
    # This time, explicitely giving the project
    config_path = prep_simple_ctx(stubbed_gcloud_ctx)
    result = CliRunner().invoke(cli, ["--ssh-config", config_path, "--not-interactive",
                                      "--project", "stub-project-1"])
    assert len([m for m in caplog.messages if "cmd" in m]) == 1
    assert_simple_run_I1(caplog, stubbed_gcloud_ctx, result)


def test_simple_run_3(caplog, stubbed_gcloud_ctx):
    # This time, using an instance list that contains instances from other project that
    # we're not selecting (this is probably redundant with some other test)
    config_path = prep_simple_ctx(stubbed_gcloud_ctx, instances="instances_2")
    result = CliRunner().invoke(cli, ["--ssh-config", config_path, "--not-interactive"])
    assert_simple_run_I1(caplog, stubbed_gcloud_ctx, result)


def test_simple_run_4(caplog, stubbed_gcloud_ctx):
    # Cover the "no diff" case by doing the simple_run twice
    config_path = prep_simple_ctx(stubbed_gcloud_ctx)
    CliRunner().invoke(cli, ["--ssh-config", config_path, "--not-interactive"])  # discarded
    result = CliRunner().invoke(cli, ["--ssh-config", config_path, "--not-interactive"])
    assert result.exit_code == 0
    assert "No changes to SSH config" in caplog.messages


def test_simple_run_5(caplog, stubbed_gcloud_ctx):
    # Cover the "no backup case"
    config_path = prep_simple_ctx(stubbed_gcloud_ctx)
    CliRunner().invoke(cli, ["--ssh-config", config_path, "--not-interactive", "--no-backup"])
    result = CliRunner().invoke(cli, ["--ssh-config", config_path, "--not-interactive"])
    assert result.exit_code == 0
    assert len([line for line in caplog.messages if "config backed up" in line]) == 0


def test_interactive_run_1(caplog, stubbed_gcloud_ctx):
    """Single project - empty configuration passed - interactive"""
    config_path = prep_simple_ctx(stubbed_gcloud_ctx)
    result = CliRunner().invoke(cli, ["--ssh-config", config_path], input="yes")
    assert_simple_run_I1(caplog, stubbed_gcloud_ctx, result)
    assert "proposed changes as a diff" in result.output
    assert "Save changes?" in result.output


def test_interactive_run_2(caplog, stubbed_gcloud_ctx):
    """Single project - empty configuration passed - interactive"""
    config_path = prep_simple_ctx(stubbed_gcloud_ctx)
    result = CliRunner().invoke(cli, ["--ssh-config", config_path], input="no")
    assert result.exit_code == 0
    assert "proposed changes as a diff" in result.output
    assert "Save changes?" in result.output
    assert "did not confirm changes. Exiting." in result.output


def test_multiproject_run_1(caplog, stubbed_gcloud_ctx):
    # Using pattern
    config_path = prep_simple_ctx(stubbed_gcloud_ctx, instances="instances_2")
    result = CliRunner().invoke(cli, ["--ssh-config", config_path, "--not-interactive",
                                      "--project", "stub-project-*"])
    assert_simple_run_I2(caplog, stubbed_gcloud_ctx, result)


def test_multiproject_run_2(caplog, stubbed_gcloud_ctx):
    # Using --all-projects
    config_path = prep_simple_ctx(stubbed_gcloud_ctx, instances="instances_2")
    result = CliRunner().invoke(cli, ["--ssh-config", config_path, "--not-interactive",
                                      "--all-projects"])
    assert_simple_run_I2(caplog, stubbed_gcloud_ctx, result)


def test_removal_run_1(caplog, stubbed_gcloud_ctx):
    # In this test we swap 'status' instances 1 and 2
    config_path = prep_simple_ctx(stubbed_gcloud_ctx,
                                  instances="instances_3", sshconfig="exhibit_5")
    result = CliRunner().invoke(cli, ["--ssh-config", config_path, "--not-interactive",
                                      "--project", "stub-project-1"])
    assert result.exit_code == 0
    with stubbed_gcloud_ctx.tmpfile("ssh_config", mode="rt") as f:
        conflines = f.readlines()
        assert len([line for line in conflines if "stubbed_instance_1" in line]) == 0
        assert len([line for line in conflines if "127.127.127.3" in line]) == 0
        assert len([line for line in conflines if "127.127.127.127" in line]) == 1
        assert len([line for line in conflines if "stubbed_instance_2" in line]) == 0


def test_removal_run_2(caplog, stubbed_gcloud_ctx):
    # Similar to removal_run_1, we swap 'status' instances 1 and 2
    # But this time we cover the "--no-remove-stopped" flag
    config_path = prep_simple_ctx(stubbed_gcloud_ctx,
                                  instances="instances_3", sshconfig="exhibit_5")
    result = CliRunner().invoke(cli, ["--ssh-config", config_path, "--not-interactive",
                                      "--project", "stub-project-1", "--no-remove-stopped"])
    assert result.exit_code == 0
    with stubbed_gcloud_ctx.tmpfile("ssh_config", mode="rt") as f:
        conflines = f.readlines()
        assert len([line for line in conflines if "stubbed_instance_1" in line]) == 1
        assert len([line for line in conflines if "127.127.127.3" in line]) == 1
        assert len([line for line in conflines if "127.127.127.127" in line]) == 1
        assert len([line for line in conflines if "stubbed_instance_2" in line]) == 0


def test_removal_run_3(caplog, stubbed_gcloud_ctx):
    # Similar to removal_run_1, but this time we setup the stubs to remove deleted instances
    config_path = prep_simple_ctx(stubbed_gcloud_ctx,
                                  instances="instances_0", sshconfig="exhibit_5")
    result = CliRunner().invoke(cli, ["--ssh-config", config_path, "--not-interactive",
                                      "--project", "stub-project-1"])
    assert result.exit_code == 0
    with stubbed_gcloud_ctx.tmpfile("ssh_config", mode="rt") as f:
        conflines = f.readlines()
        assert len(conflines) == 3  # i.e. we removed the instance


def test_removal_run_4(caplog, stubbed_gcloud_ctx):
    # Similar to removal_run_1, but this time we setup the stubs to remove deleted instances
    # And with the flag to _not_ remove it
    config_path = prep_simple_ctx(stubbed_gcloud_ctx,
                                  instances="instances_0", sshconfig="exhibit_5")
    result = CliRunner().invoke(cli, ["--ssh-config", config_path, "--not-interactive",
                                      "--project", "stub-project-1",
                                      "--no-remove-vanished"])
    assert result.exit_code == 0
    with stubbed_gcloud_ctx.tmpfile("ssh_config", mode="rt") as f:
        conflines = f.readlines()
        assert len([line for line in conflines if "stubbed_instance_1" in line]) == 1


def test_noop_unreachable_1(stubbed_gcloud_ctx):
    # I don't have machines set up this way but I suspect this may happen in the wild
    # (for instance, if you have some sort of jumpbox setup).
    # GCSS could help you in that case - but won't right now.
    config_path = prep_simple_ctx(stubbed_gcloud_ctx, instances="instances_4")
    result = CliRunner().invoke(cli, ["--ssh-config", config_path, "--not-interactive",
                                      "--project", "stub-project-1"])
    assert result.exit_code == 0
    assert "instance_5 is running but appears to be unreachable" in result.output
    assert "No changes to SSH config" in result.output


def test_auth_1(caplog, stubbed_gcloud_ctx):
    with stubbed_gcloud_ctx.db("config") as db:
        db.update({"accounts": ["test-a@gmail.com", "test-b@gmail.com"],
                   "account": "test-a@gmail.com"})
    config_path = prep_simple_ctx(stubbed_gcloud_ctx)
    result = CliRunner().invoke(cli, ["--ssh-config", config_path, "--not-interactive",
                                      "--login", "test-b@gmail.com"])
    assert result.exit_code == 0

    # Assert that we called login as requested
    assert "cmd: gcloud auth login test-b@gmail.com" in caplog.messages

    # Assert that we restored the initially set account
    with stubbed_gcloud_ctx.db("config") as db:
        assert db['account'] == 'test-a@gmail.com'


def test_auth_2(caplog, stubbed_gcloud_ctx):
    # Stub config
    with stubbed_gcloud_ctx.db("config") as db:
        db.update({"account": "test-before@gmail.com"})

    # Stub service account credentials
    with stubbed_gcloud_ctx.tmpfile("credentials.json") as f:
        sa_path = f.name
        f.write(json.dumps({"client_email": "dummy-sa@dummy-proj.iam.gserviceaccount.com"}))
        f.flush()

    config_path = prep_simple_ctx(stubbed_gcloud_ctx)
    result = CliRunner().invoke(cli, ["--ssh-config", config_path, "--not-interactive",
                                      "--service-account", sa_path])

    assert result.exit_code == 0

    # Assert that we called SA auth as requested
    assert f"cmd: gcloud auth activate-service-account --key-file={sa_path}" in caplog.messages

    # Assert that we restored the initially set account
    with stubbed_gcloud_ctx.db("config") as db:
        assert db['account'] == 'test-before@gmail.com'
