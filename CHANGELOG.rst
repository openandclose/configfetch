
Changelog
=========


v0.3.0 (2020-08-16)
-------------------

**Change:**

* Cut complex .read_file and .read_string interfaces, Add .fetch.

* Rename set_arguments -> build_arguments, set_args -> set_arguments

* Change default option_builder to DictOptionBuilder

* Cut Python 3.5

**Add:**

* Add print_dict and print_ini methods.

* Add DictOptionBuilder.

  (Old OptionPaser has renamed to FiniOptionBuilder).


v0.2.0 (2020-03-21)
-------------------

**Change:**

* Add 'None' case for BOOLEAN_STATES


v0.1.0 (2020-03-17)
-------------------

Changed significantly.
Not compatible with the previous versions.

**Change:**

* Change function syntax, to follow argparse argument syntax
  ('[=SOMETHING]' to ':: f: something').

* Cut use_dash and use_uppercase arguments in ConfigFetch.__init__

* Rename all builtin functions (stripping '_', '_comma' -> 'comma')

**Add:**

* Add 'cmds' builtin function

* Add argparse argument syntax in FINI format

* Add argparse argument building feature

* Add Python3.8


v0.0.9 (2019-02-25)
-------------------

**Add:**

* Add Python3.7

**Fix:**

* Fix _plus function (with a minute spec change)


v0.0.8 (2018-11-24)
-------------------

**Fix:**

* Fix a grave bug in Double.
  Child blank value had been overwriting parent value.


v0.0.7 (2018-05-13)
-------------------

**Fix:**

* Fix a few mistakes around ``setup.py`` (for pypi).
  No changes in the code.


v0.0.6 (2018-05-13)
-------------------

**Change:**

* Rename builtin function name ``_path()`` to ``_fmt()``

* Remove unused ``Func.__init__()`` argument ``conf``

**Add:**

* Add document (readthedocs)

**Fix:**

* Improve value selection routine.
  Now errors should be more consistent.


v0.0.5 (2017-12-08)
-------------------

* First commit
