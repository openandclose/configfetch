
Overview
========

The library provides a custom ``INI`` format,
which registers optional conversion functions for each option value.

When getting value, they are applied.

Commandline arguments and Environment Variables precedes config file values,
in that order.

All data accesses are done by ``dot access`` or ``.get()`` method.

Optionally, the custom format can register directives
to build commandline arguments
(arguments for ``argparse.ArgumentParser.add_argument``).


Installation
------------

It is a single file Python module, with no other external library dependency.

Only **Python 3.5 and above** are supported. ::

    pip install configfetch


Usage
-----

.. code:: none

    ## myapp.ini
    [main]
    log=        :: f: bool
                no

    users=      :: f: comma
                Alice, Bob, Charlie

    output=     : output format                 <-- help
                : when saving data
                : to a file.
                :: names: o                     <-- other arguments
                :: choices: ht, xht, x              for argparse
                :: default: x
                :: f: add_m, add_l              <-- functions
                ht                              <-- config value

    ## terminal
    >>> import configfetch
    >>> conf = configfetch.fetch('myapp.ini')
    >>> conf.main.log
    False
    >>> conf.main.users
    ['Alice', 'Bob', 'Charlie']
    >>> conf.main.output
    'html'

The file has optional ``:: f: something`` notations
before each option value,
which registers ``something`` function for this particular option.

Other strange (I admit) ``': '`` and ``':: '`` notations are
for building ``argparse`` arguments.
If you don't need to build the arguments, you don't need them.

---

From now on, I call this customized format, as ``Fetch-INI`` or ``FINI`` format.

I call this new configuration object as ``conf``,
to differentiate from the original ``INI`` configuration object, ``config``.


API Overview
------------

The main constructs of this module are:

class ``ConfigFetch``
    Read config files, and behave as a ``conf`` data object.

    See `API <#configfetch>`__ for details.

class ``Func``
    Keep conversion functions and apply them to values.

    See `Builin Function <#builtin-functions>`__ for included functions.

    See `User Functions <#user-functions>`__ for customization example.

function ``fetch``
    Shortcut. Using ``ConfigFetch``, return ``conf`` object.

    See `API <#fetch>`__ for details.


Value Selection
---------------

``ArgumentParser`` options and environment variable keys
(``args`` and ``envs``)
are always global, searched for in every section lookup.


Section
^^^^^^^

In the first access on ``conf``,
a section representation object (``SectionProxy``) is returned.
``args`` and ``envs`` are not involved.

    ``dot access`` (``.__getattr__(section)``)
        raise NoSectionError, when the section is not found.

    ``.get(section)``
        return ``None``,  when the section is not found.


Option
^^^^^^

In the option access (the first access on ``SectionProxy``),
``args``, ``envs``, and the section ``section`` are searched in order,
and the first valid one is *selected* (but not yet *returned*).

If ``args`` has the key, and the value is not ``None``,
it is selected (``arg``).

(Note other non-values (``''``, ``[]`` or ``False``) are selected.)

If ``envs`` has the key, and the value is not ``''``,
it is selected (``env``).

If ``section`` (or ``Default section``) has the key,
the value is selected (``opt``).

Otherwise:

    ``dot access`` (``.__getattr__(option)``)
        raise NoOptionError

    ``.get(option, fallback=_UNSET)``
        raise NoOptionError, when ``fallback`` is not provided (``_UNSET``).
        Otherwise, ``fallback`` is selected.


Nonstring
^^^^^^^^^

If the selected value is ``arg``, and it is not a string,
the value is *returned* as is.
(``env`` and ``opt`` are always a string.)

So ``ArgumentParser`` arguments that convert the value type
are just passed through.


ArgumentParser Details
^^^^^^^^^^^^^^^^^^^^^^

Normally is is better not to supply
``default`` argument of ``ArgumentParser.add_argument()``.
If it is supplied, ``arg`` is always selected.
Either the value in the commandline, or the default value.

Also take note that ``store_true`` and ``store_false`` actions
default to ``False`` and ``True`` respectively.
They are always selected, and in their case, always returned.
(above ``Nonstring`` rule).

If this is not desirable, use ``store_const`` instead. E.g.::

    parser.add_argument('--log', action='store_const', const='true')

.. note ::

    Paul Jacobson (hpaulj), active in ``argparse`` development,  discourages
    ``store_true`` and ``store_false`` in a different context. See
    `a stackoverflow <https://stackoverflow.com/a/34750557>`__.)

In most cases, you can delegate conversion to ``conf``,
by conforming to the designated ``FINI`` format. E.g.

.. code:: none

    # myapp.ini
    file=   :: f: comma
            a.txt, b.txt, c.txt

    # myapp.py
    parser.add_argument('--file', action='store')

    # terminal
    $ myapp.py --file 'a.txt, b.txt, c.txt'

instead of:

.. code:: none

    parser.add_argument('--file', action='store', nargs='+')

    $ myapp.py --file a.txt b.txt c.txt

or:

.. code:: none

    parser.add_argument('--file', action='append')

    $ myapp.py --file a.txt --file b.txt --file c.txt


Conversion
^^^^^^^^^^

The selected value is passed to the function conversion check.

If no function is registered, the value is *returned*.

If functions are registered, the value is applied to each function,
left to right in order, then the resultant value is *returned*.


Function
^^^^^^^^

Function names are searched in ``Func`` or a subclass methods.

Functions always have one argument ``value``, that is a *selected* value.
And they return one value.
It either *returns* to the caller as the end result,
or is used as the ``value`` of the next function, if any.

Functions can also access ``values``,
the original three elements list before selection (``[arg, env, opt]``).
Use ``Func.values`` attribute.


Concatenation
^^^^^^^^^^^^^

The first function must accept raw string value (initial ``value``)
as its ``value`` argument.

The second function and after may define any value type
for its ``value`` argument.

But what actually comes as ``value`` is, of course,
dependent on the previous function.

So in general users should follow the concatenation rules
each function expects.


Builtin Functions
-----------------

All builtin functions except ``bar``, expect ``value`` as a string,
so they should come in first.

``bar`` expects an list type ``value``,
so it should come the second or after.
(usually immediately after ``comma`` or ``line``.)

.. method:: bool(value)

    return ``True`` or ``False``,
    according to the same rule as ``configparser``'s.

    | ``'1'``,  ``'yes'``, ``'true'``, ``'on'`` are ``True``.
    | ``'0'``, ``'no'``, ``'false'``, ``'off'`` are ``False``.
    | Case insensitive.
    | Other values raise an error.

.. method:: comma(value)

    Return a list using comma as separators.
    No comma value returns one element list.
    Blank value returns a blank list (``[]``).

    Heading and tailing whitespaces are stripped
    from each element.

    If the previous character is ``'\'``,
    ``','`` is a literal comma, not a separator.
    This ``'\'`` is discarded.

    Any other ``'\'`` is kept as is.

    .. code::

        'aa, bb'    ->      ['aa', 'bb']
        r'aa\, bb'  ->      ['aa, bb']
        r'aa\\, bb' ->      [r'aa\, bb'])

        r'a\a'      ->      [r'a\a'])
        r'a\\a'     ->      [r'a\\a'])

.. method:: line(value)

    Return a list using line break as separators.
    No line break value returns one element list.
    Blank value returns a blank list (``[]``).

    Heading and tailing whitespaces and *commas* are stripped
    from each element.

    The escaping behavior with ``'\'`` is the same as ``comma``.

.. method:: bar(value)

    Concatenate with bar (``'|'``).

    Receive a list of strings as ``value``, return a string.

    One element list returns that element.
    Blank list returns ``''``.

    .. code::

        scheme=     :: f: comma, bar
                    https?, ftp, mailto

    .. code:: python

        >>> conf.main.scheme
        'https?|ftp|mailto'

.. method:: cmd(value)

    Return a list of strings
    ready to put in `subprocess <https://docs.python.org/3/library/subprocess.html>`__.

    Users have to quote whitespaces as they do in a terminal.

    Note ``'#'`` and after are comments, they are discarded.

    Example:

    .. code::

        command=    :: f: cmd
                    ls -l 'Live at the Apollo' # 1968

    .. code:: python

        >>> conf.main.command
        ['ls', '-l', 'Live at the Apollo']

.. method:: cmds(value)

    Return a list of list of strings.

    List version of ``cmd``.
    The input value is a list of strings, with each item made to a list by ``cmd``.

.. method:: fmt(value)

    return a string processed by ``str.format``, using ``fmts`` dictionary.
    E.g.

    .. code::

        # myapp.ini
        css=        :: f: fmt
                    {USER}/data/my.css

    .. code:: python

        # myapp.py
        fmts = {'USER': '/home/john'}

    .. code:: python

        >>> conf.main.css
        '/home/john/data/my.css'

.. method:: plus(value)

    receive ``value`` as argument, but actually it doesn't use this,
    and use ``values`` (a ``[arg, env, opt]`` list before selection) instead.

    Let's call an item starting with ``'+'`` as ``plus item``,
    one starting with ``'-'`` as ``minus item``,
    and others as ``normal item``.

    It reads each value in ``values`` in order, and:

    1) It makes a list using the same mechanism as ``comma``.
    2) If items in the list are all ``normal items``,
       then the list overwrites the previous list.
    3) If they consist only of ``plus items`` or ``minus items``,
       then it adds ``plus items`` to,
       and subtracts ``minus items`` from, the previous list.
    4) Otherwise (mixing cases), it raises error.

    Adding existing items, or subtracting nonexistent items doesn't cause errors.
    It just ignores them.

    Example:

    .. code::

        'Alice, Bob, Charlie'    -->  ['Alice', 'Bob', 'Charlie']
        '-Alice, +Dave'          -->  ['Bob', 'Charlie', 'Dave']
        '+Bob'                   -->  ['Bob', 'Charlie', 'Dave']
        '-Xavier'                -->  ['Bob', 'Charlie', 'Dave']
        'Judy, Malloy, Niaj'     -->  ['Judy', 'Malloy', 'Niaj']


User Functions
--------------

When registering user functions,

1) add them in a ``Func`` subclass
2) put ``register()`` decorator above the function
3) and call ``ConfigFetch`` with that subclass.

Example:

.. code::

    ## myapp.ini
    [main]
    search=     :: f: glob
                python

.. code:: python

    ## myapp.py
    import configfetch

    class MyFunc(configfetch.Func):

        @configfetch.register
        def glob(self, value):
            if not value.startswith('*'):
                value = '*' + value
            if not value.endswith('*'):
                value = value + '*'
            return value

    conf = configfetch.fetch('myapp.ini', Func=MyFunc)

.. code:: python

    # terminal
    >>> import myapp
    >>> conf = myapp.conf
    >>> conf.main.search
    '*python*'


FINI Syntax
-----------

``FINI`` uses ``': '`` and ``':: '`` as keywords,
designating metadata line (a space is required).
It is configurable on subclasses.

All metadata types are optional, but must follow the predetermined order. ::

    (help)
    (args)
    (func)
    value

``args`` means here, arguments for ``argparse.ArgumentParser.add_argument``.
``help`` is actually one of them, but specially treated.

help:
    Following string from ``': '`` is ``help``.
    You can repeat ``help`` on several lines.
    Strings are joined with newlines.

args:
    ``':: <name>: <value>'`` is parsed into a dictionary item,
    with some value type conversion,
    if ``<name>`` is not ``'f'``.

    ``<name>`` should be key for the argument (nargs, choices, etc.).
    special ``<name>`` ``'names'`` is used for
    `name or flags <https://docs.python.org/3/library/argparse.html#name-or-flags>`__,
    with the option name added to the last.
    (``'output'`` option in the `Usage <#usage>`__ of the document top
    becomes ``'-o', '--output'``).

func:
    Following string from ``':: f: '`` is comma separated function names
    to process the option value.

value:
    actual option value.


Configuring Arguments
---------------------

Excluding Environment Variables,
there are three kinds of option types.

1. Config-only options
2. Commandline-only options
3. Common options (to commandline and config file)

1:

If you don't provide ``help`` to an option,
it is not exposed for building process.
So that makes 1. config-only options.

2:

If you provide ``help``, but you don't provide or ignore the config option
(separating it in a specially chosen section, say,
``'[_command_only]'``),
which make 2. commandline-only options.

For this, since it is unrelated to the ``INI`` config options,
you can use any ``add_argument`` arguments.

But data types have to be guessed
from ``INI`` string values none the less,
only simple cases are feasible
(E.g. In ``':: const: 1'``, is ``'1'`` ``int`` or ``str`` ?)

See source code (``FiniOptionBuilder._convert_arg``) for details.

3:

For all common options:

    * As already said, ``help`` is required.
    * You can always add ``names``.

For Flags:

For common options which have ``bool`` in ``func``,
arguments are automatically supplied.

.. code:: ini

    log=    : log events
            :: f: bool
            yes

becomes:

.. code:: python

    [...].add_argument('--log', action='store_const', const='yes')

``action`` is always ``store_const``, ``const`` is 'yes'
(which will be converted to ``True`` when getting value).

Only to make the opposite flags, you can add ``dest`` argument.
If there is ``dest``, ``const`` is 'no' (converted to ``False``).

.. code:: ini

    no_log=     : do not log events
                :: dest: log
                :: f: bool
                no

becomes:

.. code:: python

    [...].add_argument('--no-log', action='store_const', const='no', dest='log')

For Non-Flags:

Other common options are all treated as ``action='store', nargs=None``,
which is ``argparse`` default.
Optionally you can only add ``choices``.


Building Arguments
------------------

To actually build arguments, see `build_arguments <#configfetch.ConfigFetch.set_arguments>`__.


API
---

ConfigFetch
^^^^^^^^^^^

.. autoclass:: configfetch.ConfigFetch
    :members:

fetch
^^^^^

.. autofunction:: configfetch.fetch

Double
^^^^^^

.. autoclass:: configfetch.Double

Example:

.. code:: python

    conf.japanese = Double(conf.japanese, conf.asian)

When the option is not found even in the parent section,
DEFAULT section lookup is performed, or ``NoOptionError``,
according to the uniderlined ``ConfigParser`` object
(``conf._config``).


minusadapter
^^^^^^^^^^^^

.. autofunction:: configfetch.minusadapter

Conditions:
  * ``prefix_chars`` is exactly ``'-'``
  * The argument is a registered argument
  * It's ``action`` is either ``store`` or ``append``
  * It's ``nargs`` is ``1`` or ``None``
  * The next argument starts with ``'-'``

Process:
  * long option is combined with the next argument with ``=``
  * short option is concatenated with the next argument

.. code::

    ['--file', '-myfile.txt']  -->  ['--file=-myfile.txt']
    ['-f', '-myfile.txt']      -->  ['-f-myfile.txt']

Example:

.. code:: python

    # myapp.py
    import argparse
    import configfetch
    parser = argparse.ArgumentParser()
    parser.add_argument('--file')
    args = configfetch.minusadapter(parser)
    args = parser.parse_args(args)
    print(args)

.. code-block:: console

    $ myapp.py --file -myfile.txt
    Namespace(file='-myfile.txt')

