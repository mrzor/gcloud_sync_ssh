# coding: utf-8

from datetime import datetime
import os
import re
import shutil

# from icdiff import ConsoleDiff, set_cols_option
from loguru import logger
# from ostruct import OpenStruct

from .util.color_diff import pretty_diff
from .util.case_insensitive_dict import CaseInsensitiveDict
from .host_config import HostConfig


_BEGIN_MARKER = '# Google Compute Engine Section'
_END_MARKER = '# End of Google Compute Engine Section'

_GCSS_COMMENT = """# This block has been generated by gcloud_sync_ssh
# It should be safe to edit manually."""

_RE_COMMENT = re.compile("^ *#")
_RE_EMPTY = re.compile(r"^[ \t]*$")
_RE_HOST = re.compile(r'^ *Host (.+)$')
_RE_KV = re.compile(r'^(?P<WS> *)(?P<K>[^ =]+)[ =] *(?P<V>.+)$')  # V may be quoted
_RE_PROJECT = re.compile(r'\.([^.]+)$')

_GCLOUD_KW_ORDERING = ['HostName', 'IdentityFile', 'UserKnownHostsFile', 'HostKeyAlias',
                       'IdentitiesOnly', 'CheckHostIP']


class SSHConfigParseError(RuntimeError):
    pass


# from pdb import break_on_setattr
# @break_on_setattr('dirty')
class SSHConfig(object):
    """A helper class to manipulate ~/.ssh/config file that follows `gcloud compute config-ssh`
conventions.
"""
    def __init__(self, path):
        self._path = path
        with open(os.path.expanduser(path), 'r') as _fh:
            self._lines = _fh.readlines()
            self._original_lines = self._lines.copy()
        self._parse()

    def __repr__(self):
        res = [f"SSHConfig at {self._path}\n\n"]
        res += ['{:04d} | {:s}'.format(i, l) for i, l in enumerate(self._lines)]
        return "".join(res)

    # From ssh_config(5):
    # The file contains keyword-argument pairs, one per line.  Lines starting with ‘#’ and empty
    # lines are interpreted as comments.  Arguments may optionally be enclosed in double quotes
    # (") in order to represent arguments containing spaces.  Configuration options may be sepa‐
    # rated by whitespace or optional whitespace and exactly one ‘=’ (...)
    def _parse(self):
        # This could/should be rewritten to support Match directives, optionally with a proper
        # parser that matches the config grammar 100%. This version is good enough for what
        # appears in the SSH config block in practice.
        self._hosts = {}
        self.dirty = False
        self._begin_line = None
        self._end_line = None
        current_host = None

        for i, line in enumerate(self._lines):
            if line.startswith(_BEGIN_MARKER):
                if self._begin_line:
                    raise SSHConfigParseError(f"Duplicate start marker in config on line {i}")
                self._begin_line = i
                continue

            if line.startswith(_END_MARKER):
                self._end_line = i
                # We don't break here so we can detect if the file has several GCE blocks
                # and report the error
                continue

            # XXX split for better test coverage
            if not line or _RE_EMPTY.match(line) or _RE_COMMENT.match(line):
                continue

            # We only concern ourselves with hosts defined between
            # the two markers. We skip while we're not within.
            if self._begin_line is None:
                continue
            if self._begin_line is not None and self._end_line is not None:
                continue

            # Match 'Host' lines
            host_match = _RE_HOST.match(line)
            if host_match:
                current_host = host_match[1].strip()
                self._hosts[current_host] = {'line': i, 'params': CaseInsensitiveDict()}
                continue

            # Match any other keyword=value line
            kv_match = _RE_KV.match(line)
            if kv_match:
                if not current_host:
                    logger.debug(f"Keyword `{kv_match['K']}` assignment "
                                 f"outside of Host block at line {i}")
                    continue

                self._hosts[current_host]['params'][kv_match['K']] = {
                    'line': i,
                    'value': kv_match['V'],
                    'indent': kv_match['WS']
                }
                continue

            logger.debug(f"Can't match line #{i}: {line}")

        # XXX this is outside parsing scope
        if self._begin_line is None and self._end_line is None:
            # Config doesnt have our fenced block - create one at the end
            self._lines.append("\n")
            self._lines.append(f"{_BEGIN_MARKER}\n")
            self._begin_line = len(self._lines) - 1
            self._lines.append(f"{_GCSS_COMMENT}\n")
            self._lines.append(f"{_END_MARKER}\n")
            self._end_line = len(self._lines) - 1
            self.dirty = True

        if self._begin_line is None:
            raise SSHConfigParseError("Mismatched markers. Begin marker missing ; "
                                      f"end marker at line {self._end_line}")

        if self._end_line is None:
            raise SSHConfigParseError("Mismatched markers. End marker missing ; "
                                      f"begin marker at line {self._begin_line}")

    def _append_host(self, hostname, ip, id, template):
        # XXX this should register to self._hosts for consistency (even if it's useless)
        #     (The easiest way to do this in a foolproof way is to reparse)
        assert isinstance(template, HostConfig), "template must be a HostConfig instance"
        template.HostName = ip  # XXX this mutates an argument. it's bad.
        template.HostKeyAlias = f"compute.{id}"  # XXX likewise
        new_lines = ["\n", f"Host {hostname}\n"] + template.lines(ordering=_GCLOUD_KW_ORDERING)
        for new_line in new_lines:
            self._lines.insert(self._end_line, new_line)
            self._end_line += 1
        self.dirty = True

    def _edit_host_ip(self, hostname, ip):
        params = self._hosts[hostname]["params"]
        param = params["Hostname"]  # we store the ip in the hostname parameter. confusing.

        # exit early if nothing should change
        if ip == param["value"]:
            return

        self.dirty = True
        self._lines[param["line"]] = f"{param['indent']}{params._k('Hostname')} {ip}\n"
        param["value"] = ip

    def update_host(self, hostname, ip, id, template={}):
        if hostname in self._hosts:
            self._edit_host_ip(hostname, ip)
        else:
            self._append_host(hostname, ip, id, template)

    def _host_lines(self, hostname):
        assert hostname in self._hosts
        r = [self._hosts[hostname]['line']]
        r += [pd['line'] for pd in self._hosts[hostname]["params"].values()]
        return sorted(r, reverse=True)

    def hosts_of_project(self, project_name):
        """Returns host entries in this config filtered by GCP project name"""
        def matches_project(hostname):
            match = _RE_PROJECT.search(hostname)
            return project_name == match[1] if match else False
        return {k: v for k, v in self._hosts.items() if matches_project(k)}

    def remove_host(self, hostname):
        if hostname not in self._hosts:
            return None

        # Remove Host line
        lines_to_remove = self._host_lines(hostname)
        for i in lines_to_remove:
            del self._lines[i]

        # Remove associated kwarg lines
        offset_to_substract = len(lines_to_remove)
        last_line_to_remove = lines_to_remove[-1]
        for host, data in self._hosts.items():
            if data['line'] > last_line_to_remove:
                data['line'] -= offset_to_substract

                for ph in data['params'].values():
                    ph['line'] -= offset_to_substract

        # Remove from internal structures
        del self._hosts[hostname]

        # Set dirty
        self.dirty = True

        # Return amount of lines deleted
        return offset_to_substract

    # XXX: Aggressive removal based on hostname parsing allows removing _deleted_ instances
    #      as well
    # def remove_hosts(self, project_name, whitelist=[]):
    #    pass

    # XXX: Restore this very superior version based on icdiff whenever they ship to PyPY
    # def diff(self, **diff_args):
    #     """See icdiff.ConsoleDiff.make_table args for diff_args"""
    #     if not self.dirty:
    #         return None

    #     # Prepare differ based on icdiff magic
    #     options = OpenStruct()
    #     set_cols_option(options)  # This finds out terminal width in a platform independent way
    #     cdiff = ConsoleDiff(cols=options.cols, line_numbers=True)

    #     # Run it and return the good stuff
    #     diff_args.setdefault("fromdesc", self._path)
    #     diff_args.setdefault("todesc", "proposed")
    #     diff_args.setdefault("context", True)
    #     diff_args.setdefault("numlines", 1)
    #     return cdiff.make_table(self._original_lines, self._lines, **diff_args)

    def diff(self, **diff_args):
        if not self.dirty:
            return None
        return pretty_diff(self._original_lines, self._lines,
                           fromdesc=self._path, todesc="proposed changes",
                           context_lines=2)

    def backup(self, tag=None, filename=None):
        tag = tag if tag else datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = filename if filename else f"{self._path}.backup.{tag}"
        if os.path.exists(backup_filename):
            raise RuntimeError(f"Can't backup config to {backup_filename} - file exists")

        shutil.copy2(os.path.expanduser(self._path), os.path.expanduser(backup_filename))
        return backup_filename

    def save(self):
        with open(os.path.expanduser(self._path), "w") as fh:
            for line in self._lines:
                fh.write(line)
            fh.flush()

        self._original_lines = self._lines.copy()
        self.dirty = False
        self._parse()
        return self._path

    def infer_host_config(self):
        """Creates a Host configuration that matches all the _common_ kwargs in this
           configuration."""
        if len(self._hosts) == 0:
            return HostConfig()
        first_host = list(self._hosts.values())[0]

        # Find keywords defined for all hosts
        common_keys = set(first_host['params'].keys())
        for host in self._hosts.values():
            common_keys &= set(host['params'].keys())

        # For each of the common keywords, find those whose argument is stable (does not change
        # between different kwargs)
        stable_kwargs = {}
        for k in common_keys:
            stable = True
            v = first_host['params'][k]['value']
            for host in self._hosts.values():
                stable &= host['params'][k]['value'] == v
            if stable:
                stable_kwargs[k] = v
        return HostConfig(**stable_kwargs)
