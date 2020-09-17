import contextlib
import logging
import os
import shutil

import pytest
from _pytest.logging import caplog as _caplog  # noqa:F401
from loguru import logger

from json_dict import JsonDict


# Loguru/Pytest caplog replacement fixture
@pytest.fixture
def caplog(_caplog):  # noqa:F811
    class PropogateHandler(logging.Handler):
        def emit(self, record):
            logging.getLogger(record.name).handle(record)

    handler_id = logger.add(PropogateHandler(), format="{message}")
    yield _caplog
    logger.remove(handler_id)


DB_NAMES = {"cmd_log", "config", "instances", "projects"}


@pytest.helpers.register
@contextlib.contextmanager
def env_override(env_var_name, env_var_value):
    """
    Simple context manager that allows to temporarily set an environment variable, then
    restore its value afterwards.
    """
    previous_value = os.getenv(env_var_name)  # Save
    os.environ[env_var_name] = env_var_value  # Override
    yield  # Use
    # Restore
    if previous_value is None:
        os.environ.pop(env_var_name)
    else:
        os.environ[env_var_name] = previous_value


@pytest.fixture
def raise_on_gcloud_instance_sync():
    with env_override("GCSS_RAISE_ON_INSTANCE_SYNC", "1"):
        yield


# Stubbed gcloud setup/teardown
# (Prefer usage as a fixture)
@pytest.helpers.register
class StubbedGCloudContext:
    """
    Context-manager used to setup the various stub files for our stubbed gcloud
    implementation.

    Its main goal is conciseness of use above of all else - notably, above clarity or
    expressiveness.

    Prefer the stubbed_gcloud_ctx fixture to using this as is.
    """

    # XXX is there a way to create a tmpfs for this (/tmp may or may not be a tmpfs in practice)
    def __init__(self, tmp_path):
        self._saved_db_path = None
        self._saved_path = None
        self.tmp_path = tmp_path
        self._db_path = tmp_path.joinpath("db")

    def __enter__(self):
        # XXX this now could be implemented using a cascade of a couple of env_override contexts
        #     instead of this (which would, however, be largely the same)
        # Save pre-existing environment (if any) for the vars we have to set
        self._saved_db_path = os.getenv("GCLOUD_DB_PATH", "")
        os.environ["GCLOUD_DB_PATH"] = str(self._db_path)

        # Setup PATH
        self._saved_path = os.getenv('PATH', "")
        here_path = os.path.dirname(__file__)
        new_path = f"{here_path}:{self._saved_path}" if self._saved_path else here_path
        os.environ['PATH'] = new_path

        logger.trace(f"SGCC[{id(self)}].__enter__")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Restore saved values
        os.environ['PATH'] = self._saved_path
        os.environ['GCLOUD_DB_PATH'] = self._saved_db_path
        logger.trace(f"SGCC[{id(self)}].__exit__")

    def _db_json_path(self, tablename):
        return f"{self._db_path}.{tablename}.json"

    def stub_path(self, basename):
        return os.path.dirname(os.path.abspath(__file__)) + \
            f"/stubfiles/{basename}.json"

    def config_path(self, basename):
        return os.path.dirname(os.path.abspath(__file__)) + \
            f"/configfiles/{basename}"

    def db(self, tablename):
        """Return a JsonDict for a specific 'tablename' i.e. a single json file."""
        assert tablename in DB_NAMES
        return JsonDict(__path__=self._db_json_path(tablename))

    def seed_db(self, tablename, seed_basename):
        """Copy seed data from stubfiles directory into this context tmp folder."""
        seed_fullname = self.stub_path(seed_basename)
        if not os.path.exists(seed_fullname):
            raise RuntimeError(f"No file found for {seed_basename} at {seed_fullname}")
        shutil.copy(seed_fullname, self._db_json_path(tablename))

    def seed_configfile(self, basename, seed_basename):
        seed_fullname = self.config_path(seed_basename)
        if not os.path.exists(seed_fullname):
            raise RuntimeError(f"No file found for {seed_basename} at {seed_fullname}")
        stubfile_path = self.tmp_path.joinpath(basename)
        shutil.copy(seed_fullname, stubfile_path)
        return stubfile_path

    def tmpfile(self, filename, mode="wt"):
        """Convenience to open a (probably new) file inside the tmp_path underlying this ctx"""
        return open(str(self.tmp_path.joinpath(filename)), mode=mode)


@pytest.fixture
def stubbed_gcloud_ctx(tmp_path):
    with StubbedGCloudContext(tmp_path) as ctx:
        yield ctx
