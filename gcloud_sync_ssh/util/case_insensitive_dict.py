class CaseInsensitiveDict(dict):
    """A dict that allows access case-insensitively while keeping original key casing intact.

       Not designed for speed. Should be 2 to 3 times slower than an usual dict in most cases.

       Very inspired by https://stackoverflow.com/questions/2082152/case-insensitive-dictionary.
"""

    # Doc that I'd wish I could state:
    # Because this dict is based on a dict of keys, it opts to intern keys derived from
    # interned strings. I.e. if you pass an interned key, the derived key will be interned
    # as well. You can turn off this behavior by setting _interning=False.
    # XXX could not find a way to figure out whether or not a string was interned

    @classmethod
    def _lowkey(cls, key):
        return key.casefold() if isinstance(key, str) else key

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lowkeys = {}
        self._register_keys()
        self._interning = False

    def __getitem__(self, key):
        return super().__getitem__(self._k(key))

    def __setitem__(self, key, value):
        super().__setitem__(self._k(key), value)
        self._register_key(key)  # 'canonical' casing is the FIRST seen

    def __delitem__(self, key):
        result = super().__delitem__(self._k(key))
        self._forget_key(key)
        return result

    def __contains__(self, key):
        return super().__contains__(self._k(key))

    def pop(self, key, *args, **kwargs):
        lowkey = self.__class__._lowkey(key)
        # _lowkeys.pop should only default to key if this pop defaults too
        key = self._lowkeys.pop(lowkey, key)
        return super().pop(key, *args, **kwargs)

    def popitem(self):
        result = super().popitem()
        self._forget_key(result[0])
        return result

    def get(self, key, *args, **kwargs):
        return super().get(self._k(key), *args, **kwargs)

    def setdefault(self, key, *args, **kwargs):
        return super().setdefault(self._k(key), *args, **kwargs)

    def update(self, E={}, **F):
        # Probably more than 3x slower than super
        for k, v in E.items():
            self[k] = v

        for k, v in F.items():
            self[k] = v

    def _forget_key(self, key):
        """Internal."""
        lowkey = self.__class__._lowkey(key)
        self._lowkeys.pop(lowkey, None)

    def _register_key(self, key):
        """Sets the original casing for key once, then no-ops."""
        assert key in self
        lowkey = self.__class__._lowkey(key)
        if lowkey not in self._lowkeys:
            self._lowkeys[lowkey] = key

    def _register_keys(self):
        """Internal"""
        for k in self.keys():
            self._register_key(k)

    def _k(self, key):
        """Get the original casing for string key if there is one or return key"""
        return self._lowkeys.get(self.__class__._lowkey(key), key)

    def rekey(self, new_key):
        """Changes the canonical casing for a key"""
        self[new_key] = self.pop(new_key)

    # XXX IMPL: __eq__

    # XXX IMPL: PEP-584 support ( __ror__ ; __ior__ ; __or__ for dicts )
