
Overview
========

The library provides a custom ``INI`` format,
which registers optional conversion functions for each option value.

When getting value, they are applied.

Commandline arguments and Environment Variables precedes config file values,
in that order.

All data accesses are done by ``dot access`` or ``.get()`` method.


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
    log=        [=BOOL] no
    users=      [=COMMA] Alice, Bob, Charlie
    output=     html

    # terminal
    >>> import configfetch
    >>> conf = configfetch.fetch('myapp.ini')
    >>> conf.main.log
    False
    >>> conf.main.users
    ['Alice', 'Bob', 'Charlie']
    >>> conf.output
    'html'

The file has optional ``[=SOMETHING]`` notations
before each option value,
which registers ``_something()`` function for this particular option.

Let's call this customized format as ``Fetch-INI`` or ``FINI`` format.

Let's call this new configuration object as ``conf``,
as opposed to ``config``, the original ``INI`` configuration object.


Limitations
-----------

*Manual Arguments Building*

While the script can *parse* commandline arguments automatically,
it is the same as before, in that
you have to manually register each argument with ``ArgumentParser``, e.g.::

    parser.add_argument('--output')

*ConfigParser.converters*

ConfigParser already has a value conversion mechanism
(`.converters <https://docs.python.org/3/library/configparser.html#customizing-parser-behaviour>`__).
In this, it is the caller who has to designate appropriate functions,
``.getint()``, ``.getsomething()``, etc.
Maybe this is good enough for many cases.

*Function Arguments*

Users can customize their own functions.
But precisely because our only interfaces are
``dot access`` and ``.get()``,
functions can't accept arguments other than
miscellaneous internal config values.
So they need some workarounds in that case.
(e.g. create custom functions with arguments already internalized.)


API Overview
------------

The main constructs of this module are:

class ``ConfigFetch``
    Read config files, and behave as a ``conf`` data object.

    See `API <#configfetch>`__ for details.

class ``Func``
    Keep conversion functions and apply them to values.

    See `Func <api.html#configfetch.Func>`__ for the builtin Functions.

    See `User Functions <#user-functions>`__ for customization.

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
    file=   [COMMA] a.txt, b.txt, c.txt

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

Function names must start with ``'_'``.

The matching string is made from one in ``FINI`` file,
adding this ``'_'``, and converting to lowercase. E.g.
``[=SOMETHING]`` to ``_something``.

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

All builtin functions except ``_bar()``, expect ``value`` as a string,
so they should come in first.

``_bar()`` expects an list type ``value``,
so it should come the second or after.
(usually immediately after ``_comma()`` or ``_line()``.)

.. method:: _bool(value)

    return ``True`` or ``False``,
    according to the same rule as ``configparser``'s.

    | ``'1'``,  ``'yes'``, ``'true'``, ``'on'`` are ``True``.
    | ``'0'``, ``'no'``, ``'false'``, ``'off'`` are ``False``.
    | Case insensitive.
    | Other values raise an error.

.. method:: _comma(value)

    Return a list using comma as separators.
    No comma value returns one element list.
    Blank value returns a blank list (``[]``).

    Heading and tailing whitespaces are stripped
    from each element.

.. method:: _line(value)

    Return a list using line break as separators.
    No line break value returns one element list.
    Blank value returns a blank list (``[]``).

    Heading and tailing whitespaces and *commas* are stripped
    from each element.

.. method:: _bar(value)

    Concatenate with bar (``'|'``).

    Receive a list of strings as ``value``, return a string.

    One element list returns that element.
    Blank list returns ``''``.

    .. code::

        scheme=     [=COMMA][=BAR] https?, ftp, mailto

    .. code:: python

        >>> conf.main.scheme
        'https?|ftp|mailto'

.. method:: _cmd(value)

    Return a list of strings
    ready to put in `subprocess <https://docs.python.org/3/library/subprocess.html>`__.

    Users have to quote whitespaces as they do in a terminal.

    Note ``'#'`` and after are comments, they are discarded.

    Example:

    .. code::

        command=    [=CMD] ls -l 'Live at the Apollo' # 1968

    .. code:: python

        >>> conf.main.command
        ['ls', '-l', 'Live at the Apollo']

.. method:: _cmds(value)

    Return a list of list of strings.

    List version of ``_cmd``.
    The input value is a list of strings, with each item made to a list by ``_cmd``.

.. method:: _fmt(value)

    return a string processed by ``str.format``, using ``fmts`` dictionary.
    E.g.

    .. code::

        # myapp.ini
        css=        [=FMT] {USER}/data/my.css

    .. code:: python

        # myapp.py
        fmts = {'USER': '/home/john'}

    .. code:: python

        >>> conf.main.css
        '/home/john/data/my.css'

.. method:: _plus(value)

    receive ``value`` as argument, but actually it doesn't use this,
    and use ``values`` (a ``[arg, env, opt]`` list before selection) instead.

    Let's call an item starting with ``'+'`` as ``plus item``,
    one starting with ``'-'`` as ``minus item``,
    and others as ``normal item``.

    It reads each value in ``values`` in order, and:

    1) It makes a list using the same mechanism as ``_comma()``.
    2) If items in the list are all ``normal items``,
       then the list overwrites the previous list.
    3) If they consist only of ``plus items`` or ``minus items``,
       then it adds ``plus items`` to,
       and subtracts ``minus items`` from, the previous list.
    4) Otherwise (mixing cases), it raises error.

    Adding existing items, or subtracting nonexistant items doesn't cause errors.
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
    search=     [=GLOB] python

.. code:: python

    ## myapp.py
    import configfetch

    class MyFunc(configfetch.Func):

        @configfetch.register
        def _glob(self, value):
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


API
---

ConfigFetch
^^^^^^^^^^^

.. autoclass:: configfetch.ConfigFetch
    :members:

Note:

You can select custom ``ConfigParser`` object for ``_config``,
by argument ``parser``,
but ``_ctxs`` is hard-coded to use an ordinary ``ConfigParser``.
It may interfere with something.

Regardless of ``use_dash`` argument, ``argparse`` does this
dash-to-underscore conversion for their own argument names.
So it is normally better to keep it ``True``,
and maintain correspondence.


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


minusadapter()
^^^^^^^^^^^^^^

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

