import json
import os

from loguru import logger


class JsonDict(dict):
    """
    Stupid simple synchronous json-backed dict.

    Can be used as a contextmanager, in which case the dict will be json saved upon exiting
    context. Saves can be forced by calling `commit`.
    """
    def __init__(self, *args, **kwargs):
        """
        Initializes and behaves like a regular dict.

        The __path__ key must be specified and should point at the backing JSON file location.
        The __path__ key is special and cannot be used by the underlying dict.
        """
        self.path = kwargs.pop("__path__")
        super().__init__(*args, **kwargs)

        if os.path.exists(self.path):
            with open(self.path, "r") as fd:
                saved_data = json.load(fd)
                self.update(saved_data)
                logger.trace(f"loaded {saved_data} from {self.path}")

    def commit(self):
        with open(self.path, "w") as f:
            f.write(json.dumps(self))
            f.flush()  # Should not be required. But it is.

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.commit()

    def __repr__(self):
        return f"JsonDict@{self.path}"

    def __str__(self):
        return f"JsonDict@{self.path} {super().__repr__()}"
