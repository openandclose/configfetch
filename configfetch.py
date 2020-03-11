
"""Helper to get values from configparser and argparse."""

import argparse
from collections import OrderedDict
import configparser
import os
import re
import shlex
import sys

_UNSET = object()

# Record available function names for value conversions.
# After the module initialization, this list is populated.
_REGISTRY = set()


class Error(Exception):
    """Base Exception class for the module.

    ``configparser`` has 11 custom Exceptions scattered in 14 methods,
    the last time I checked.
    I'm not going to wrap except the most relevant ones.
    """


class NoSectionError(Error, configparser.NoSectionError):
    """Raised when no section is found."""


class NoOptionError(Error, configparser.NoOptionError):
    """Raised when no option is found."""

    def __init__(self, option, section):
        super().__init__(option, section)


def register(meth):
    """Decorate value functions to populate global value `_REGISTRY`."""
    _REGISTRY.add(meth.__name__)
    return meth


def _make_func_dict(registry):
    """Make a dictionary with uppercase keys.

    ``_comma`` -> ``{'COMMA': '_comma'}``
    """
    return {func.lstrip('_').upper(): func for func in registry}


def _make_func_regex(registry):
    r"""Make regex expression to parse custom ``INI`` (``FINI``) syntax.

    ``['_comma', '_bar']`` -> ``(?:[=(COMMA)]|[=(BAR)])\s*``.
    """
    formats = _make_func_dict(registry).keys()
    formats = '|'.join([r'\[=(' + fmt + r')\]' for fmt in formats])
    formats = r'\s*(?:' + formats + r')\s*'
    return re.compile(formats)


def _parse_comma(value):
    if value:
        return [val.strip()
                for val in value.split(',') if val.strip()] or []
    return []


def _parse_line(value):
    if value:
        return [val.strip(' ,')
                for val in value.split('\n') if val.strip()] or []
    return []


class Func(object):
    """Register and apply value conversions.

    Normally always initialized and called from main classes internally.
    """

    BOOLEAN_STATES = {  # the same as ConfigParser.BOOLEAN_STATES
        '1': True, 'yes': True, 'true': True, 'on': True,
        '0': False, 'no': False, 'false': False, 'off': False}

    def __init__(self, ctx, fmts):
        self._ctx = ctx
        self._fmts = fmts

    @register
    def _bool(self, value):
        if value.lower() not in self.BOOLEAN_STATES:
            raise ValueError('Not a boolean: %s' % value)
        return self.BOOLEAN_STATES[value.lower()]

    @register
    def _comma(self, value):
        return _parse_comma(value)

    @register
    def _line(self, value):
        return _parse_line(value)

    @register
    def _bar(self, value):
        """Concatenate with bar (``'|'``).

        Receive a list of strings as ``value``, return a string.
        """
        if not isinstance(value, list):
            msg = "'configfetch.Func._bar()' accepts only 'list'. Got %r"
            raise ValueError(msg % str(value))
        if any(value):
            return '|'.join(value)
        else:
            return ''

    @register
    def _cmd(self, value):
        """Return a list of strings, useful for ``subprocess`` (stdlib)."""
        return shlex.split(value, comments='#')

    @register
    def _cmds(self, value):
        """List version of ``_cmd``."""
        return [self._cmd(v) for v in value]

    @register
    def _fmt(self, value):
        """Return a string processed by ``str.format``."""
        return value.format(**self._fmts)

    @register
    def _plus(self, value):
        """Implement ``plusminus option`` (my neologism).

        Main logic is in `_get_plusminus_values`.
        Presuppose values are not processed.
        """
        values = self.values
        return _get_plusminus_values(reversed(values))

    def _get_value(self, values):
        arg, env, conf = values
        if arg not in (_UNSET, None):
            value = arg
        elif env not in (_UNSET, ''):
            value = env
        elif conf is not _UNSET:
            value = conf
        else:
            value = _UNSET
        return value

    def _get_funcname(self, option):
        funcdict = _make_func_dict(_REGISTRY)
        funcnames = []
        if self._ctx:
            if self._ctx.get(option):
                for f in self._ctx.get(option).split(','):
                    f = f.strip()
                    funcnames.append(funcdict[f])
        return funcnames

    def _get_func(self, option):
        funcnames = self._get_funcname(option)
        return [getattr(self, fn) for fn in funcnames]

    def _format_value(self, option, values, func):
        value = self._get_value(values)
        if value is _UNSET:
            raise NoOptionError(option, self._ctx.name)
        if not func:
            return value
        for f in func:
            value = f(value)
        return value

    def __call__(self, option, values):
        func = self._get_func(option)
        self.values = values
        value = self._format_value(option, values, func)
        return value


class ConfigFetch(object):
    """A custom Configuration object.

    It keeps two ``ConfigParser`` object (``_config`` and ``_ctxs``).

    ``_config`` is an ordinary one.
    ``_ctxs`` is one which keeps function names for each option.
    Option access returns a value already functions applied.

    It also has ``argparse.Namespace`` object (args),
    and Environment variable dictionay (envs).

    They are global, having no concept of sections.
    If the option name counterpart is defined,
    their value precedes the config value.


    The class ``__init__`` should accept
    all ``ConfigParser.__init__`` keyword arguments.
    The class specific argumants are:

    :param fmts: dictionay ``Func._fmt`` uses
    :param args: ``argparse.Namespace`` object,
        already commandline arguments parsed
    :param envs: dictionary with Environment Variable name and value
        as key and value
    :param Func: ``Func`` or subclasses, keep actual functions
    :param parser: ``ConfigParser`` or subclasses,
        keep actual config data
    :param use_dash: if True, you can use dashes for option names
        (change dashes to underscores Internally)
    :param use_uppercase: if True, option names are case sensitive.
        (usuful if commandline wants to use case sensitive argument names)
    """

    def __init__(self, *, fmts=None, args=None, envs=None, Func=Func,
            parser=configparser.ConfigParser,
            use_dash=True, use_uppercase=True, **kwargs):
        self._fmts = fmts or {}
        self._args = args or argparse.Namespace()
        self._envs = envs or {}
        self._Func = Func
        self._parser = parser
        self._cache = {}

        optionxform = self._get_optionxform(use_dash, use_uppercase)

        config = parser(**kwargs)
        config.optionxform = optionxform

        # ctxs(contexts) is also a ConfigParser object, not just a dictionary,
        # because of ``default_section`` handling.
        ctxs = configparser.ConfigParser(
            default_section=config.default_section)
        ctxs.optionxform = config.optionxform

        self._config = config
        self._ctxs = ctxs

    def read_file(self, f, format=None):
        """Read config from an opened file object.

        :param f: a file object
        :param format: 'fini', 'ini' or ``None``

        If ``format`` is 'fini',
        read config values, and function definitions ([=SOMETHING]).
        Previous definitions are overwritten, if any.

        If ``format`` is 'ini' (or actually any other string than 'fini'),
        read only config values, definitions are kept intact.

        If ``format`` is ``None`` (default),
        only when the definitions dict (``_ctxs``) is blank,
        read the file as 'fini'
        (supposed to be the first time read).
        Otherwise read the file as 'ini'.
        """
        self._config.read_file(f)
        self._check_and_parse_config(format)

    def read_string(self, string, format=None):
        """Read config from a string.

        :param string: a string
        :param format: 'fini', 'ini' or ``None``

        The meaning of ``format`` is the same as ``.read_file``.
        """
        self._config.read_string(string)
        self._check_and_parse_config(format)

    def _get_optionxform(self, use_dash, use_uppercase):
        def _xform(option):
            if use_dash:
                option = option.replace('-', '_')
            if not use_uppercase:
                option = option.lower()
            return option
        return _xform

    def _check_and_parse_config(self, format):
        if format is None:
            if len(self._ctxs._sections) == 0:
                format = 'fini'
        if format == 'fini':
            self._parse_config()

    def _parse_config(self):
        ctxs = self._ctxs
        for secname, section in self._config.items():
            if secname not in ctxs:  # not in sections and default_section
                ctxs.add_section(secname)
            ctx = ctxs[secname]
            for option in section:
                self._parse_option(section, option, ctx)

    def _parse_option(self, section, option, ctx):
        value = section[option]
        func_regex = _make_func_regex(_REGISTRY)

        func = []
        while True:
            match = func_regex.match(value)
            if match:
                # ``match.groups()`` should be ``None``'s except one.
                f = [g for g in match.groups() if g][0]
                func.append(f)
                value = value[match.end():]
            else:
                break

        section[option] = value
        if func:
            # ``ctxs`` is a ``configparser`` object,
            # so option values must be a string.
            ctx[option] = ','.join(func)

    # TODO:
    # Invalidate section names this class reserves.
    # cf.
    # >>> set(dir(configfetch.fetch(''))) - set(dir(object()))

    def __getattr__(self, section):
        if section in self._cache:
            return self._cache[section]

        if section in self._ctxs:
            ctx = self._ctxs[section]
        else:
            ctx = self._ctxs[self._ctxs.default_section]

        s = SectionProxy(
            self, section, ctx, self._fmts, self._Func)
        self._cache[section] = s
        return s

    def get(self, section):
        try:
            return self.__getattr__(section)
        except NoSectionError:
            # follows dictionary's ``.get()``
            return None

    def __iter__(self):
        return self._config.__iter__()


class SectionProxy(object):
    """``ConfigFetch`` section proxy object.

    Similar to ``ConfigParser``'s proxy object.
    """

    def __init__(self, conf, section, ctx, fmts, Func):
        self._conf = conf
        self._config = conf._config
        self._section = section
        self._ctx = ctx
        self._fmts = fmts
        self._Func = Func

        # 'ConfigParser.__contains__()' includes default section.
        if self._get_section() not in self._config:
            raise NoSectionError(self._get_section())

    # Introduce small indirection,
    # in case it needs special section manipulation in user subclasses.
    # ``None`` option case must be provided
    # for section verification in `__init__()`.
    def _get_section(self, option=None):
        return self._section

    def _get_conf(self, option, fallback=_UNSET, convert=False):
        section = self._get_section(option)
        try:
            value = self._config.get(section, option)
        except configparser.NoOptionError:
            return fallback

        if convert:
            value = self._convert(option, (value, _UNSET, _UNSET))
        return value

    def _get_arg(self, option):
        if self._conf._args and option in self._conf._args:
            return getattr(self._conf._args, option)
        return _UNSET

    def _get_env(self, option):
        env = None
        if self._conf._envs and option in self._conf._envs:
            env = self._conf._envs[option]
        if env and env in os.environ:
            return os.environ[env]
        return _UNSET

    def _get_values(self, option):
        return [self._get_arg(option),
                self._get_env(option),
                self._get_conf(option)]

    def __getattr__(self, option):
        values = self._get_values(option)
        return self._convert(option, values)

    def _convert(self, option, values):
        # ``arg`` may have non-string value.
        # it returns it as is (not raising Error).
        arg = values[0]
        if arg not in (_UNSET, None):
            if not isinstance(arg, str):
                return arg
        f = self._get_func()
        return f(option, values)

    def _get_funcname(self, option):
        f = self._get_func()
        return f._get_funcname(option)

    def _get_func(self):
        return self._Func(self._ctx, self._fmts)

    def get(self, option, fallback=_UNSET):
        try:
            return self.__getattr__(option)
        except NoOptionError:
            if fallback is _UNSET:
                raise
            else:
                return fallback

    # Note it does not do any reverse-formatting.
    def set_value(self, option, value):
        section = self._get_section(option)
        self._config.set(section, option, value)

    def __iter__(self):
        return self._config[self._section].__iter__()


class Double(object):
    """Supply a parent section to fallback, before 'DEFAULT'.

    An accessory helper class,
    not so related to this module's main concern.

    Default section is a useful feature of ``INI`` format,
    but it is always global and unconditional.
    Sometimes more fine-tuned one is needed.

    :param sec: ``SectionProxy`` object
    :param parent_sec: ``SectionProxy`` object to fallback
    """

    def __init__(self, sec, parent_sec):
        self.sec = sec
        self.parent_sec = parent_sec

    def __getattr__(self, option):
        funcnames = self.sec._get_funcname(option)
        if funcnames == ['_plus']:
            return self._get_plus_value(option)
        else:
            return self._get_value(option)

    def _get_value(self, option):
        # Blank values are None, '', and []. 'False' should be excluded.

        # spec:
        # No preference between blank values. Just returns parent one.
        try:
            val = self.sec.get(option)
        except NoOptionError:
            parent_val = self.parent_sec.get(option)
            return parent_val

        if val in (None, '', []):
            try:
                parent_val = self.parent_sec.get(option)
                return parent_val
            except NoOptionError:
                pass

        return val

    def _get_plus_value(self, option):
        parent_val = self.parent_sec._get_conf(option)
        values = self.sec._get_values(option)
        values = values + [parent_val]
        self._check_unset(values, option, self.sec._ctx.name)
        return _get_plusminus_values(reversed(values))

    def get(self, option, fallback=_UNSET):
        try:
            return self.__getattr__(option)
        except ValueError:
            if fallback is _UNSET:
                raise
            else:
                return fallback

    def _check_unset(self, values, section, option):
        if all([value is _UNSET for value in values]):
            raise NoOptionError(section, option)

    def __iter__(self):
        return self.sec.__iter__()


def fetch(file_or_string, *, encoding=None,
        fmts=None, args=None, envs=None, Func=Func,
        parser=configparser.ConfigParser,
        use_dash=True, use_uppercase=True, **kwargs):
    """Fetch ``ConfigFetch`` object.

    It is a convenience function for the basic use of the library.
    Most arguments are the same as ``ConfigFetch.__init__``.

    the specific arguments are:

    :param file_or_string: a filename to open
        if the name is in system path, or a string
    :param encoding: encoding to use when openning the name

    Files are read with ``format=None``.
    """
    conf = ConfigFetch(fmts=fmts, args=args, envs=envs, Func=Func,
        parser=parser, use_dash=use_dash, use_uppercase=use_uppercase)

    if os.path.isfile(file_or_string):
        with open(file_or_string, encoding=encoding) as f:
            conf.read_file(f)
    else:
        conf.read_string(file_or_string)
    return conf


def _get_plusminus_values(adjusts, initial=None):
    """Add or sbtract values partially (used by ``_plus()``).

    Use ``+`` and ``-`` as the markers.

    :param adjusts: lists of values to process in order
    :param initial: initial values (list) to add or subtract further
    """
    def _fromkeys(keys):
        return OrderedDict.fromkeys(keys)

    values = _fromkeys(initial) if initial else _fromkeys([])

    for adjust in adjusts:
        # if not adjust:
        if adjust in (_UNSET, None, '', []):
            continue
        if not isinstance(adjust, str):
            fmt = 'Each input should be a string. Got %r(%r)'
            raise ValueError(fmt % (type(adjust), str(adjust)))
        adjust = _parse_comma(adjust)

        if not any([a.startswith(('+', '-')) for a in adjust]):
            values = _fromkeys(adjust)
            continue

        for a in adjust:
            cmd, a = a[:1], a[1:]
            if a and cmd == '+':
                if a not in values:
                    values[a] = None
            elif a and cmd == '-':
                if a in values:
                    del values[a]
            else:
                fmt = ('Input members must be '
                    "'+something' or '-something', or none of them. Got %r.")
                raise ValueError(fmt % (cmd + a))
    return list(values.keys())


def minusadapter(parser, matcher=None, args=None):
    """Edit ``option_arguments`` with leading dashes.

    An accessory helper function.
    It unites two arguments to one, if the second argument starts with ``'-'``.

    The reason is that ``argparse`` cannot parse this particular pattern.

    | https://bugs.python.org/issue9334
    | https://stackoverflow.com/a/21894384

    And ``_plus`` uses this type of arguments frequently.

    :param parser: ArgumentParser object,
        already actions registered
    :param matcher: regex string to match options,
        to narrow the targets
        (``None`` means to process all arguments)
    :param args: arguments list to parse, defaults to ``sys.argv[1:]``
        (the same as ``argparse`` default)
    """
    def _iter_args(args, actions):
        args = iter(args)
        for arg in args:
            if arg in actions:
                if '=' not in arg:
                    try:
                        val = next(args)
                    except StopIteration:
                        yield arg
                        raise
                    if val.startswith('-'):
                        if arg.startswith('--'):
                            yield '%s=%s' % (arg, val)
                            continue
                        elif arg.startswith('-'):
                            yield '%s%s' % (arg, val)
                            continue
                    else:
                        yield arg
                        yield val
                        continue
            yield arg

    if not parser.prefix_chars == '-':
        return args

    actions = []
    classes = (argparse._StoreAction, argparse._AppendAction)
    for a in parser._actions:
        if isinstance(a, classes):
            if a.nargs in (1, None):
                for opt in a.option_strings:
                    if matcher:
                        if not re.match(matcher, opt):
                            continue
                    actions.append(opt)

    args = args if args else sys.argv[1:]
    return list(_iter_args(args, actions))
