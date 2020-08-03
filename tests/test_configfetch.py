
import argparse
import configparser
import textwrap

import pytest

import configfetch

fetch = configfetch.fetch


def f(string):
    return textwrap.dedent(string.strip('\n'))


def _get_action(conf, option_strings):
    parser = argparse.ArgumentParser(prog='test')
    conf.build_arguments(parser)
    # parser.print_help()
    for action in parser._get_optional_actions():
        if option_strings in action.option_strings:
            break
    return action
    raise ValueError('No action with option_strings: %r' % option_strings)


class TestEscapedSplit:

    def check_comma(self, value, expected):
        ret = configfetch._parse_comma(value)
        assert ret == expected

    def check_line(self, value, expected):
        ret = configfetch._parse_line(value)
        assert ret == expected

    def test_comma(self):
        self.check_comma('aaaa', ['aaaa'])
        self.check_comma(r'\aaaa', [r'\aaaa'])
        self.check_comma(r'aa\aa', [r'aa\aa'])
        self.check_comma(r'aaa\a', [r'aaa\a'])
        self.check_comma(r'aaaa\\', [r'aaaa\\'])

        self.check_comma(r'aa\\aa', [r'aa\\aa'])
        self.check_comma(r'aa\\\aa', [r'aa\\\aa'])

        self.check_comma('aa, bb', ['aa', 'bb'])
        self.check_comma(r'aa\, bb', ['aa, bb'])
        self.check_comma(r'aa\\, bb', [r'aa\, bb'])
        self.check_comma(r'aa\\\, bb', [r'aa\\, bb'])

        self.check_comma(r'aa\a, bb', [r'aa\a', 'bb'])
        self.check_comma(r'aa\\a, bb', [r'aa\\a', 'bb'])
        self.check_comma(r'aa\\\a, bb', [r'aa\\\a', 'bb'])

        self.check_comma(',aa', ['aa'])
        self.check_comma('aa,', ['aa'])
        self.check_comma('aa,,', ['aa'])

    def test_line(self):
        self.check_line('aa\nbb', ['aa', 'bb'])
        self.check_line('aa\\\nbb', ['aa\nbb'])
        self.check_line('aa\\\\\nbb', ['aa\\\nbb'])
        self.check_line('aa\\\\\\\nbb', ['aa\\\\\nbb'])

        self.check_line('aa\nbb,', ['aa', 'bb,'])

class TestInheritance:

    def test_iter(self):
        data = f("""
        [sec1]
        [sec2]
        """)
        conf = fetch(data)
        assert list(conf.__iter__()) == ['DEFAULT', 'sec1', 'sec2']

    def test_iter_option(self):
        data = f("""
        [sec1]
        aa = xxx
        bb = yyy
        """)
        conf = fetch(data)
        assert list(conf.sec1.__iter__()) == ['aa', 'bb']

    def test_contains(self):
        data = f("""
        [sec1]
        [sec2]
        """)
        conf = fetch(data)
        assert 'sec2' in conf

    def test_contains_option(self):
        data = f("""
        [sec1]
        aa = xxx
        bb = yyy
        """)
        conf = fetch(data)
        assert 'bb' in conf.sec1


class TestParseConfig:

    def test_conf_str(self):
        data = f("""
        [sec1]
        aa = xxx
        """)
        conf = fetch(data)
        assert conf.sec1.aa == 'xxx'

    def test_conf_str_blank(self):
        data = f("""
        [sec1]
        """)
        conf = fetch(data)
        with pytest.raises(configfetch.NoOptionError):
            assert conf.sec1.aa == ''

    def test_conf_str_nosection(self):
        data = f("""
        [sec1]
        aa = xxx
        """)
        conf = fetch(data)
        with pytest.raises(configfetch.NoSectionError):
            assert conf.sec2

    def test_conf_str_default(self):
        data = f("""
        [DEFAULT]
        aa = xxx
        [sec1]
        """)
        conf = fetch(data)
        assert conf.sec1.aa == 'xxx'

    def test_conf_str_default_nosection(self):
        data = f("""
        [DEFAULT]
        aa = xxx
        """)
        conf = fetch(data)
        with pytest.raises(configfetch.NoSectionError):
            assert conf.sec1.aa == 'xxx'

    def test_conf_str_default_read_section(self):
        data = f("""
        [DEFAULT]
        aa = xxx
        """)
        conf = fetch(data)
        data = f("""
        [sec1]
        """)
        conf._config.read_string(data)
        assert conf.sec1.aa == 'xxx'

    def test_conf_str_default_blank(self):
        data = f("""
        [DEFAULT]
        [sec1]
        """)
        conf = fetch(data)
        with pytest.raises(configfetch.NoOptionError):
            assert conf.sec1.aa == ''

    def test_conf_str_default_blank_nosection(self):
        data = ''
        conf = fetch(data)
        with pytest.raises(configfetch.NoSectionError):
            assert conf.sec1.aa == ''

    def test_conf_bool(self):
        data = f("""
        [sec1]
        aa = :: f: bool
             Yes
        """)
        conf = fetch(data)
        assert conf.sec1.aa is True

    def test_conf_bool_no(self):
        data = f("""
        [sec1]
        aa = :: f: bool
             No
        """)
        conf = fetch(data)
        assert conf.sec1.aa is False

    # blank string returns ``None``
    def test_conf_bool_blank(self):
        data = f("""
        [sec1]
        aa = :: f: bool
              
        """)
        conf = fetch(data)
        assert conf.sec1.aa is None

    def test_conf_comma(self):
        data = f("""
        [sec1]
        aa = :: f: comma
             xxx1, xxx2, xxx3
        """)
        conf = fetch(data)
        assert conf.sec1.aa == ['xxx1', 'xxx2', 'xxx3']

    def test_conf_comma_indent(self):
        data = f("""
        [sec1]
        aa = :: f: comma
             xxx1, xxx2,
            xxx3
        """)
        conf = fetch(data)
        assert conf.sec1.aa == ['xxx1', 'xxx2', 'xxx3']

    def test_conf_comma_newline(self):
        data = f("""
        [sec1]
        aa = :: f: comma
             xxx1, xxx2
             xxx3
        """)
        conf = fetch(data)
        assert conf.sec1.aa == ['xxx1', 'xxx2\nxxx3']

    def test_conf_comma_blank(self):
        data = f("""
        [sec1]
        aa = :: f: comma
              
        """)
        conf = fetch(data)
        assert conf.sec1.aa == []

    def test_conf_line(self):
        data = f("""
        [sec1]
        aa = :: f: line
             xxx1
             xxx2
             xxx3
        """)
        conf = fetch(data)
        assert conf.sec1.aa == ['xxx1', 'xxx2', 'xxx3']

    def test_conf_line_comma(self):
        data = f("""
        [sec1]
        aa = :: f: line
             xxx1
             xxx2
             xxx3, xxx4
        """)
        conf = fetch(data)
        assert conf.sec1.aa == ['xxx1', 'xxx2', 'xxx3, xxx4']

    def test_conf_line_blank(self):
        data = f("""
        [sec1]
        aa = :: f: line
              
        """)
        conf = fetch(data)
        assert conf.sec1.aa == []

    def test_conf_line_multiblanks(self):
        data = f("""
        [sec1]
        aa = :: f: line
              
            
            
        """)
        conf = fetch(data)
        assert conf.sec1.aa == []

    def test_conf_bar_comma(self):
        data = f("""
        [sec1]
        aa = :: f: comma, bar
             xxx1, xxx2, xxx3
        """)
        conf = fetch(data)
        assert conf.sec1.aa == 'xxx1|xxx2|xxx3'

    def test_conf_bar_comma_blank(self):
        data = f("""
        [sec1]
        aa = :: f: comma, bar
              
        """)
        conf = fetch(data)
        assert conf.sec1.aa == ''

    def test_conf_bar_comma_blank_spaces(self):
        data = f("""
        [sec1]
        aa = :: f: comma, bar
                 
        """)
        conf = fetch(data)
        assert conf.sec1.aa == ''

    def test_conf_bar_line(self):
        data = f("""
        [sec1]
        aa = :: f: line, bar
             xxx1
             xxx2
             xxx3
        """)
        conf = fetch(data)
        assert conf.sec1.aa == 'xxx1|xxx2|xxx3'

    def test_conf_bar_line_blank(self):
        data = f("""
        [sec1]
        aa = :: f: line, bar
              
        """)
        conf = fetch(data)
        assert conf.sec1.aa == ''

    def test_conf_bar_line_blank_spaces(self):
        data = f("""
        [sec1]
        aa = :: f: line, bar
                 
        """)
        conf = fetch(data)
        assert conf.sec1.aa == ''

    def test_conf_cmd(self):
        data = f("""
        [sec1]
        aa = :: f: cmd
             --aaa -b "ccc cc" ddd,dd
        """)
        conf = fetch(data)
        assert conf.sec1.aa == ['--aaa', '-b', 'ccc cc', 'ddd,dd']

    def test_conf_cmds(self):
        data = f("""
        [sec1]
        aa = :: f: line, cmds
             ls *.txt
             find . "aaa"
        """)
        conf = fetch(data)
        assert conf.sec1.aa == [['ls', '*.txt'], ['find', '.', 'aaa']]

    def test_conf_fmt(self):
        data = f("""
        [sec1]
        aa = :: f: fmt
             {USER}/data/my.css
        """)
        conf = fetch(data, fmts={'USER': '/home/john'})
        assert conf.sec1.aa == '/home/john/data/my.css'


class TestParseContexts:

    def test_ctx_default_bool(self):
        data = f("""
        [DEFAULT]
        aa = :: f: bool
             no
        [sec1]
        """)
        conf = fetch(data)
        assert conf.sec1.aa is False

    def test_ctx_default_bool_noop(self):
        data = f("""
        [DEFAULT]
        aa = :: f: bool
              
        [sec1]
        aa = no
        """)
        conf = fetch(data)
        assert conf.sec1.aa is False

    def test_ctx_default_comma(self):
        data = f("""
        [DEFAULT]
        aa = :: f: comma
              
        [sec1]
        aa = xxx1, xxx2, xxx3
        """)
        conf = fetch(data)
        assert conf.sec1.aa == ['xxx1', 'xxx2', 'xxx3']


class TestParseFunc:

    def test_func_newline(self):
        data = f("""
        [sec1]
        aa =
            :: f: bool
            no
        """)
        conf = fetch(data)
        assert conf.sec1.aa is False


# Just checking the standard library's behaviors.
class TestConfigParser:

    def test_indent(self):
        data = f("""
        [sec1]
          aa =
           xxx
        """)
        config = configparser.ConfigParser()
        config.read_string(data)
        assert config['sec1']['aa'] == '\nxxx'

        data = f("""
        [sec1]
          aa =
          xxx
        """)
        config = configparser.ConfigParser()
        with pytest.raises(configparser.ParsingError):
            config.read_string(data)

    def test_allow_no_value(self):
        data = f("""
        [sec1]
        aa =
            :: f: bool
              no
        """)
        config = configparser.ConfigParser(allow_no_value=True)
        config.read_string(data)
        assert config['sec1']['aa'] == '\n:: f: bool\nno'


class TestArgparse:

    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--aa')
    parser.add_argument('-b', '--bb')
    parser.add_argument('-c', '--cc', action='store_const', default='', const='yes')
    parser.add_argument('-d', '--no-cc', action='store_const', const='no', dest='cc')
    parser.add_argument('-e', '--ee-eee')

    def get_args(self, cmd):
        return self.parser.parse_args(cmd)

    def test_args_and_conf(self):
        data = f("""
        [sec1]
        aa = xxx
        """)
        args = self.get_args(['--aa', 'axxx'])
        conf = fetch(data, args=args)
        assert conf.sec1.aa == 'axxx'

    def test_args_and_conf_short(self):
        data = f("""
        [sec1]
        aa = xxx
        """)
        args = self.get_args(['-a', 'axxx'])
        conf = fetch(data, args=args)
        assert conf.sec1.aa == 'axxx'

    def test_args_and_conf_none(self):
        data = f("""
        [sec1]
        aa = xxx
        """)
        args = self.get_args([])
        conf = fetch(data, args=args)
        assert conf.sec1.aa == 'xxx'

    def test_args_and_conf_const(self):
        data = f("""
        [sec1]
        cc = :: f: bool
        """)
        args = self.get_args(['--cc'])
        conf = fetch(data, args=args)
        assert conf.sec1.cc is True

    def test_args_and_conf_const_false(self):
        data = f("""
        [sec1]
        cc = :: f: bool
             true
        """)
        args = self.get_args(['--no-cc'])
        conf = fetch(data, args=args)
        assert conf.sec1.cc is False

    def test_args_and_conf_dash(self):
        data = f("""
        [sec1]
        ee_eee = xxx
        """)
        args = self.get_args(['-e', 'axxx'])
        conf = fetch(data, args=args)
        assert conf.sec1.ee_eee == 'axxx'


class _CustomFunc(configfetch.Func):
    """Used the test below."""

    @configfetch.register
    def custom(self, value):
        return 'test'


class TestCustomize:

    def test_customfunc(self):
        data = f("""
        [sec1]
        aa = :: f: custom
             xxx
        """)
        conf = fetch(data, Func=_CustomFunc)
        assert conf.sec1.aa == 'test'


class TestDouble:

    def test_nooption_nooption(self):
        data = f("""
        [sec1]
        aa = xxx
        """)
        conf1 = fetch(data)
        data = f("""
        [sec1]
        aa = yyy
        """)
        conf2 = fetch(data)
        double = configfetch.Double(conf2.sec1, conf1.sec1)
        with pytest.raises(configfetch.NoOptionError):
            assert double.bb == 'zzz'

    def test_nooption_blank(self):
        data = f("""
        [sec1]
        aa = xxx
        """)
        conf1 = fetch(data)
        data = f("""
        [sec1]
        bb =
        """)
        conf2 = fetch(data)
        double = configfetch.Double(conf2.sec1, conf1.sec1)
        assert double.bb == ''

    def test_blank_nooption(self):
        data = f("""
        [sec1]
        bb =
        """)
        conf1 = fetch(data)
        data = f("""
        [sec1]
        aa = yyy
        """)
        conf2 = fetch(data)
        double = configfetch.Double(conf2.sec1, conf1.sec1)
        assert double.bb == ''

    def test_blank_blank(self):
        data = f("""
        [sec1]
        bb =
        """)
        conf1 = fetch(data)
        data = f("""
        [sec1]
        bb = :: f: comma
              
        """)
        conf2 = fetch(data)
        double = configfetch.Double(conf2.sec1, conf1.sec1)
        assert double.bb == ''

    def test_plus(self):
        data = f("""
        [sec1]
        aa = :: f: plus
             xxx, yyy
        """)
        conf1 = fetch(data)
        data = f("""
        [sec1]
        aa = :: f: plus
             -yyy
        """)
        conf2 = fetch(data)
        double = configfetch.Double(conf2.sec1, conf1.sec1)
        assert double.aa == ['xxx']


class TestGetPlusMinusValues:

    initial = ['aaa', 'bbb', 'ccc']

    def compare(self, adjusts, initial, expected):
        values = configfetch._get_plusminus_values(adjusts, initial)
        assert values == expected

    def test_adjusts_argument(self):
        args = (['ddd'], None, ['ddd'])
        self.compare(*args)
        args = (['+ddd'], None, ['ddd'])
        self.compare(*args)
        args = (['-bbb'], None, [])
        self.compare(*args)

        args = (['ddd'], self.initial, ['ddd'])
        self.compare(*args)
        args = (['+ddd'], self.initial, ['aaa', 'bbb', 'ccc', 'ddd'])
        self.compare(*args)
        args = (['-bbb'], self.initial, ['aaa', 'ccc'])
        self.compare(*args)

        args = (['-aaa, -bbb'], self.initial, ['ccc'])
        self.compare(*args)
        args = (['-aaa, +ddd, +eee'], self.initial,
            ['bbb', 'ccc', 'ddd', 'eee'])
        self.compare(*args)


class TestMinusAdapter:

    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--aa', action='store_const', const='A')
    parser.add_argument('-b', '--bb', action='store_true')
    parser.add_argument('-c', '--cc', action='store_false')
    parser.add_argument('-d', '--dd', action='append')
    parser.add_argument('-e', '--ee', action='append_const', const='E')
    parser.add_argument('-f', '--ff', action='count')

    parser.add_argument('-x', '--xx')
    parser.add_argument('-y', '--yy', nargs=1)

    def compare(self, args, new_args, matcher=None):
        assert configfetch.minusadapter(self.parser, matcher, args) == new_args

    def test(self):
        # No Minus argument
        args = ['--aa', '--xx', 'xxxx', '--bb']
        new_args = ['--aa', '--xx', 'xxxx', '--bb']
        self.compare(args, new_args)

        # Minus argument
        args = ['--aa', '--xx', '-xxxx', '--bb']
        new_args = ['--aa', '--xx=-xxxx', '--bb']
        self.compare(args, new_args)

        # Minus with another StoreAction
        args = ['--aa', '--xx', '-xxxx', '--yy', 'yyyy']
        new_args = ['--aa', '--xx=-xxxx', '--yy', 'yyyy']
        self.compare(args, new_args)

        # Minus with AppendAction
        args = ['--dd', '-dddd', '--xx', '-xxxx', '--bb']
        new_args = ['--dd=-dddd', '--xx=-xxxx', '--bb']
        self.compare(args, new_args)

        # Minus, short option version
        args = ['--aa', '-x', '-xxxx', '--bb']
        new_args = ['--aa', '-x-xxxx', '--bb']
        self.compare(args, new_args)


class TestParseArgs:

    def test_help(self):
        data = f("""
        [sec1]
        aa = : help string
             :: f: comma
             xxx1, xxx2
        """)
        conf = fetch(data)
        args = conf._ctx['aa']['argparse']
        assert args['help'] == 'help string'

    def test_help_multilines(self):
        data = f("""
        [sec1]
        aa = : This
             : is a
             : help.
             :: f: comma
             xxx1, xxx2
        """)
        conf = fetch(data)
        args = conf._ctx['aa']['argparse']
        assert args['help'] == 'This\nis a\nhelp.'

    def test_help_multilines_blank(self):
        # testing both ':' and ': '
        data = f("""
        [sec1]
        aa = : This
             : is a
             :
             : 
             : help.
             :: f: comma
             xxx1, xxx2
        """)
        conf = fetch(data)
        args = conf._ctx['aa']['argparse']
        assert args['help'] == 'This\nis a\n\n\nhelp.'

    def test_help_and_choices(self):
        data = f("""
        [sec1]
        aa = : help string
             :: choices: ss, tt
             tt
        """)
        conf = fetch(data)
        args = conf._ctx['aa']['argparse']
        assert args['help'] == 'help string'
        assert args['choices'] == ['ss', 'tt']


class TestBuildArgs:

    def test_help(self):
        data = f("""
        [sec1]
        aa = : help string
             :: f: comma
             xxx1, xxx2
        """)
        conf = fetch(data)
        action = _get_action(conf, '--aa')
        assert isinstance(action, argparse._StoreAction)
        assert action.help == 'help string'

    def test_help_and_choices(self):
        data = f("""
        [sec1]
        aa = : help string
             :: choices: ss, tt
             tt
        """)
        conf = fetch(data)
        action = _get_action(conf, '--aa')
        assert isinstance(action, argparse._StoreAction)
        assert action.choices == ['ss', 'tt']

    def test_names(self):
        data = f("""
        [sec1]
        aa = : help string
             :: names: a
             true
        """)
        conf = fetch(data)
        action = _get_action(conf, '--aa')
        assert isinstance(action, argparse._StoreAction)
        assert action.option_strings == ['-a', '--aa']

    def test_bool(self):
        data = f("""
        [sec1]
        aa = : help string
             :: f: bool
             yes
        """)
        conf = fetch(data)
        action = _get_action(conf, '--aa')
        assert isinstance(action, argparse._StoreConstAction)
        assert action.const == 'yes'

    def test_bool_opposite(self):
        data = f("""
        [sec1]
        aa =    : help string
                :: f: bool
                yes
        no_aa = : help string2
                :: dest: aa
                :: f: bool
                no
        """)
        conf = fetch(data)
        parser = argparse.ArgumentParser(prog='test')
        conf.build_arguments(parser)
        namespace = parser.parse_args(['--aa'])
        assert namespace.__dict__['aa'] == 'yes'
        namespace = parser.parse_args(['--no-aa'])
        assert namespace.__dict__['aa'] == 'no'

    def test_bool_default_no(self):
        data = f("""
        [sec1]
        overwrite = : help string
                    :: f: bool
                    no
        """)
        conf = fetch(data)
        action = _get_action(conf, '--overwrite')
        assert isinstance(action, argparse._StoreConstAction)
        assert action.const == 'yes'

    def test_bool_opposite_default_no(self):
        data = f("""
        [sec1]
        overwrite =     : help string
                        :: f: bool
                        no
        no_overwrite =  : help string2
                        :: dest: overwrite
                        :: f: bool
                        yes
        """)
        conf = fetch(data)
        parser = argparse.ArgumentParser(prog='test')
        conf.build_arguments(parser)
        namespace = parser.parse_args(['--overwrite'])
        assert namespace.__dict__['overwrite'] == 'yes'
        namespace = parser.parse_args(['--no-overwrite'])
        assert namespace.__dict__['overwrite'] == 'no'


class TestBuildArgsCommandlineOnly:

    def test_int(self):
        data = f("""
        [sec1]
        aa = : help string
             :: default: 1
             xxx
        """)
        conf = fetch(data)
        action = _get_action(conf, '--aa')
        assert isinstance(action, argparse._StoreAction)
        assert action.default == 1

    def test_int_like_string(self):
        data = f("""
        [sec1]
        aa = : help string
             :: default: '1'
             xxx
        """)
        conf = fetch(data)
        action = _get_action(conf, '--aa')
        assert isinstance(action, argparse._StoreAction)
        assert action.default == '1'

    def test_type(self):
        data = f("""
        [sec1]
        aa = : help string
             :: type: int
             42
        """)
        conf = fetch(data)
        action = _get_action(conf, '--aa')
        assert isinstance(action, argparse._StoreAction)
        assert action.type == int

    def test_suppress(self):
        data = f("""
        [DEFAULT]
        aa = : argparse.SUPPRESS
             :: default: argparse.SUPPRESS
        [sec1]
        aa = xxx
        """)
        conf = fetch(data)
        action = _get_action(conf, '--aa')
        assert isinstance(action, argparse._StoreAction)
        assert action.help == argparse.SUPPRESS
        assert action.default == argparse.SUPPRESS
        assert conf.sec1.aa == 'xxx'


def test_print_data():
    data = f("""
    [DEFAULT]
    aa = aaa
    [sec1]
    bb = bbb
    cc = : help string
         :: names: c
         :: f: bool
         ccc
    dd =
    """)

    dict_string = f("""
    {
        'DEFAULT': {
            'aa': {
                'value': 'aaa',
            },
        },
        'sec1': {
            'bb': {
                'value': 'bbb',
            },
            'cc': {
                'argparse': {
                    'help': 'help string',
                    'names': ['c'],
                },
                'func': ['bool'],
                'value': 'ccc',
            },
            'dd': {
                'value': '',
            },
        },
    }
    """)
            
    ini_string = f("""
    [DEFAULT]
    aa= aaa

    [sec1]
    bb= bbb
    cc= ccc
    dd=

    """)

    conf = fetch(data, option_builder=configfetch.FiniOptionBuilder)
    printer = configfetch.ConfigPrinter

    ret = []
    printer(conf, print=ret.append).print_dict()
    assert '\n'.join(ret) == dict_string[:-1]

    ret = []
    printer(conf, print=ret.append).print_ini()
    assert '\n'.join(ret) == ini_string[:-1]
