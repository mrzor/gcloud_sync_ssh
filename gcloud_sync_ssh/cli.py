#!/usr/bin/env python3

from contextlib import contextmanager, suppress
import sys
import typing

import click
from loguru import logger
from pydantic import ValidationError

from . import __version__
from .gcloud_auth import GCloudServiceAccountAuth, GCloudAccountIdAuth
from .gcloud_config import gcloud_config_get
from .gcloud_instances import build_host_dict
from .gcloud_projects import fetch_projects_data
from .host_config import HostConfig
from .util.case_insensitive_dict import CaseInsensitiveDict
from .util.globbing import has_pattern, matches_any
from .ssh_config import SSHConfig, SSHConfigParseError


@contextmanager
def nullcontext():
    yield


def _sync_instances(project_id, instance_globs, ssh_config, host_template,
                    no_remove_stopped, no_remove_vanished):
    data = build_host_dict(project_id, instance_globs)

    host_statuses = [datum['status'] for datum in data.values()]
    status_recap_dict = {status: host_statuses.count(status) for status in set(host_statuses)}
    status_recap_list = [f"{status_recap_dict[status]} {status}"
                         for status in sorted(status_recap_dict)]
    status_recap = ", ".join(status_recap_list)
    logger.info(f"[{project_id}] Instance status: {status_recap}")

    seen_hosts = set()
    for host, hd in data.items():
        seen_hosts.add(host)
        # See https://cloud.google.com/compute/docs/instances/instance-life-cycle
        # for status state machine

        # We ignore transitional states and suspension-related cases
        if hd['status'] == 'RUNNING':
            if hd['ip']:
                ssh_config.update_host(host, ip=hd['ip'], id=hd['id'], template=host_template)
            else:
                # XXX there is an argument to be made for removing the instance here
                pass

        if hd['status'] == 'TERMINATED':
            if not no_remove_stopped:
                ssh_config.remove_host(host)

    # Remove vanished/deleted instances
    if not no_remove_vanished:
        config_hosts = ssh_config.hosts_of_project(project_id)
        for host in (set(config_hosts.keys()) - seen_hosts):
            ssh_config.remove_host(host)


def _prepare_auth_context(login=None, service_account=None):
    ctx = nullcontext()
    if login:
        if service_account:
            logger.error("--login and --service-account cannot be used simultaneously")
            exit(1)
        ctx = GCloudAccountIdAuth(login)
    elif service_account:
        ctx = GCloudServiceAccountAuth(service_account)
    return ctx


def _pp_validation_errors(ex):
    for err in ex.errors():
        t = err["type"]
        field = err["loc"][0]
        if t == "value_error.extra":
            logger.error(f"field {field} is not supported")
        else:
            logger.error(f"{t} in field {field} : {err['msg']}")


def _build_host_template(inferred_kwargs={}, no_host_defaults=[], cli_kwargs=[]):
    """Prepares our template HostConfig for hosts we are going to discover"""
    # XXX: hosts we need to update don't use the template at all, but could, to batch edit)

    # Prepare keyword->field case insensitive lookup dict
    dummy_config = HostConfig()
    keywords = CaseInsensitiveDict()
    for field_name, field_metadata in dummy_config.__fields__.items():
        keywords[field_name] = field_metadata

    # 1) Start with defaults
    if no_host_defaults:
        kwargs = {}
    else:
        kwargs = HostConfig.default_config().minidict()

    # 2) Override default with inferred kwargs
    kwargs.update(inferred_kwargs)

    # 3) Finally override with kwargs from the commandline
    # XXX doesn't support lists yet
    for kwarg in cli_kwargs:
        try:
            eq_idx = kwarg.index("=")
        except ValueError:
            logger.error(f"Invalid KWArg '{kwarg}' - must be Keyword=Argument")
            exit(1)
        k = keywords._k(kwarg[:eq_idx])  # Use canonical casing of keyword
        v = kwarg[eq_idx+1:]
        if v:  # We are setting a value
            # Deal with keywords that can be specified multiple times
            # NB: typing.get_origin is 3.8+ - we are 3.6+, so we must explicitely
            #     check for all multivalued types available. Fortunately, it's just List[str]
            #     (for now).
            if k in keywords and keywords[k].outer_type_ is typing.List[str]:
                if k not in kwargs:
                    kwargs[k] = [v]  # We don't have any, set it up as a list
                else:
                    kwargs[k].append(v)  # We have (we hope) a list, append to it
            else:
                # Simple case (last input on CLI wins)
                kwargs[k] = v
        else:  # We are unsetting a value
            kwargs.pop(k, None)

    try:
        return HostConfig(**kwargs)
    except ValidationError as e:
        _pp_validation_errors(e)
        exit(1)


@click.command()
@click.argument("INSTANCE_GLOBS", nargs=-1, type=str, required=False)
@click.option("-V", "--version", is_flag=True, default=False,
              help="Show version and leave")
@click.option("-l", "--login", type=str,
              help="Perform gcloud auth to a specific account before running")
@click.option("-s", "--service-account", type=str, metavar="AUTH_PATH",
              help="Perform gcloud auth to a specific service account before running")
@click.option("-P", "--all-projects", is_flag=True,
              help="Synchronize instances in all reachable projects")
@click.option("-p", "--project", type=str, multiple=True, metavar="PROJECT_NAME",
              help="Synchronize instances in a specific project (can be specified several times)")
@click.option("-c", "--ssh-config", type=str,
              help="Path the SSH config file", metavar="CONFIG_PATH",
              default="~/.ssh/config")
@click.option("-ni", "--not-interactive", is_flag=True, default=False,
              help="Don't show diff and don't ask approval before writing updated config file.")
@click.option("-kw", "--kwarg", type=str, multiple=True,
              metavar="KW=[ARG]",
              help="""(for all hosts) Set specific SSH Keyword-Argument (kwarg) pairs

Ex: "-kw StrictHostKeyChecking=ask" to set

Ex: "-kw StrictHostKeyChecking=" to remove the field
""")
@click.option("-nk", "--no-host-key-alias", is_flag=True, default=False,
              help="(for all hosts) Don't generate a HostKeyAlias entry based on instance id")
@click.option("--no-inference", is_flag=True, default=False,
              help="(for new hosts) Don't infer kwargs from existing Hosts")
@click.option("-nd", "--no-host-defaults", is_flag=True, default=False,
              help="(for new hosts) Don't use baked in kwargs defaults")
@click.option("-nrs", "--no-remove-stopped", is_flag=True, default=False,
              help="(for existing, stopped hosts) Don't remove STOPPED instances from config.")
@click.option("-nrv", "--no-remove-vanished", is_flag=True, default=False,
              help="(for existing, unlistable hosts) Don't remove "
              "vanished/deleted instances from config.")
@click.option("-dt", "--debug-template", is_flag=True, default=False,
              help="Display 'Host' template and exit")
@click.option("--no-backup", is_flag=True, default=False,
              help="Don't save SSH configuration backup.")
def cli(instance_globs,
        login, service_account,
        all_projects, project,
        ssh_config, kwarg,
        version, debug_template, not_interactive,
        no_inference, no_backup, no_host_defaults, no_host_key_alias,
        no_remove_stopped, no_remove_vanished):
    """An improved version of `gcloud compute config-ssh`.
       See https://github.com/mrzor/gcloud_sync_ssh/blob/master/README.md for more info."""

    # Version
    if version:
        logger.info(f"gcloud_sync_ssh {__version__}")
        return

    # Remove pre-configured logger
    with suppress(ValueError):
        logger.remove(0)

    # Configure logger
    log_format = '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | ' \
        '<level>{level: <8}</level> | ' \
        '<level>{message}</level>'  # Simpler format, but still pretty
    logger.add(sys.stderr, format=log_format, level="INFO")  # Change default log level

    if project and all_projects:
        logger.error("--project and --all-projects cannot be used simultaneously")
        exit(1)

    # Load config (exit before any IPC if it's wrong)
    try:
        _ssh_config = SSHConfig(ssh_config)
    except SSHConfigParseError as e:
        logger.error(f"SSH Config parse error: {e}")
        exit(1)

    # Prepare Host template
    inferred_kwargs = _ssh_config.infer_host_config().minidict() if not no_inference else {}
    host_template = _build_host_template(inferred_kwargs=inferred_kwargs,
                                         no_host_defaults=no_host_defaults,
                                         cli_kwargs=kwarg)
    if debug_template:
        logger.info("Displaying host template")
        print(''.join(host_template.lines()))
        logger.info("Done displaying host template")
        return

    # Prepare gcloud auth context
    ctx = _prepare_auth_context(login=login, service_account=service_account)

    # Try to obtain active project name if no projects are specified in options
    if not all_projects and not project:
        project = [gcloud_config_get("core/project")]
        if not project[0]:
            logger.error("could not determine an active project")
            exit(1)

    # Prepare project list
    project_list = None
    if not all_projects and not has_pattern(project):
        # One or more simple --project options were passed, use "as is"
        project_list = project
    else:
        assert all_projects or has_pattern(project)  # ? obviously
        # Either we want all projects, or we have some patterns to match against all projects
        logger.info("Enumerating reachable GCP projects")
        if has_pattern(project):
            project_list = [datum["projectId"] for datum in fetch_projects_data()
                            if matches_any(datum["projectId"], project)]
        else:
            project_list = [datum["projectId"] for datum in fetch_projects_data()]

    # Do what we're here to do
    logger.info(f"Beginning instance enumeration in {len(project_list)} projects")
    with ctx:  # Restoring our gcloud auth when we're done
        for project in project_list:
            logger.info(f"[{project}] Enumerating instances")
            _sync_instances(project, instance_globs, _ssh_config, host_template,
                            no_remove_stopped, no_remove_vanished)

    # Check what's new
    diff = _ssh_config.diff()
    if not diff:
        logger.info("No changes to SSH config")
        return

    # Display diff and ask for confirmation
    if not not_interactive:
        logger.info("Displaying proposed changes as a diff before applying")
        for line in diff:
            click.echo(line)

        confirmed = None
        try:
            confirmed = click.confirm("Save changes?", default=False)
        except click.Abort:
            confirmed = False

        if not confirmed:
            logger.info("User did not confirm changes. Exiting.")
            exit(0)

    # Backup config file
    if not no_backup:
        backup_filename = _ssh_config.backup()
        logger.info(f"Previous SSH config backed up to {backup_filename}")

    # Finally save the rewritten confirm
    config_filename = _ssh_config.save()
    logger.info(f"Rewrote SSH config file at {config_filename}")

    # We are done.
