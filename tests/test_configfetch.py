
import argparse
import configparser

import pytest

import configfetch

fetch = configfetch.fetch
j = '\n'.join



class TestInheritance:

    def test_iter(self):
        data = j(['[sec1]', '[sec2]'])
        conf = fetch(data)
        assert list(conf.__iter__()) == ['DEFAULT', 'sec1', 'sec2']

    def test_iter_option(self):
        data = j(['[sec1]', 'aa = xxx', 'bb = yyy'])
        conf = fetch(data)
        assert list(conf.sec1.__iter__()) == ['aa', 'bb']

    def test_contains(self):
        data = j(['[sec1]', '[sec2]'])
        conf = fetch(data)
        assert 'sec2' in conf

    def test_contains_option(self):
        data = j(['[sec1]', 'aa = xxx', 'bb = yyy'])
        conf = fetch(data)
        assert 'bb' in conf.sec1


class TestParseConfig:

    def test_conf_str(self):
        data = j(['[sec1]', 'aa = xxx'])
        conf = fetch(data)
        assert conf.sec1.aa == 'xxx'

    def test_conf_str_blank(self):
        data = j(['[sec1]'])
        conf = fetch(data)
        with pytest.raises(configfetch.NoOptionError):
            assert conf.sec1.aa == ''

    def test_conf_str_nosection(self):
        data = j(['[sec1]', 'aa = xxx'])
        conf = fetch(data)
        with pytest.raises(configfetch.NoSectionError):
            assert conf.sec2

    def test_conf_str_default(self):
        data = j(['[DEFAULT]', 'aa = xxx', '[sec1]'])
        conf = fetch(data)
        assert conf.sec1.aa == 'xxx'

    def test_conf_str_default_nosection(self):
        data = j(['[DEFAULT]', 'aa = xxx'])
        conf = fetch(data)
        with pytest.raises(configfetch.NoSectionError):
            assert conf.sec1.aa == 'xxx'

    def test_conf_str_default_read_section(self):
        data = j(['[DEFAULT]', 'aa = xxx'])
        conf = fetch(data)
        data = j(['[sec1]'])
        conf._config.read_string(data)
        assert conf.sec1.aa == 'xxx'

    def test_conf_str_default_blank(self):
        data = j(['[DEFAULT]', '[sec1]'])
        conf = fetch(data)
        with pytest.raises(configfetch.NoOptionError):
            assert conf.sec1.aa == ''

    def test_conf_str_default_blank_nosection(self):
        data = j([''])
        conf = fetch(data)
        with pytest.raises(configfetch.NoSectionError):
            assert conf.sec1.aa == ''

    def test_conf_bool(self):
        data = j(['[sec1]', 'aa = [=BOOL] Yes'])
        conf = fetch(data)
        assert conf.sec1.aa is True

    def test_conf_bool_no(self):
        data = j(['[sec1]', 'aa = [=BOOL] No'])
        conf = fetch(data)
        assert conf.sec1.aa is False

    def test_conf_bool_blank(self):
        data = j(['[sec1]', 'aa = [=BOOL]'])
        conf = fetch(data)
        with pytest.raises(ValueError):
            assert conf.sec1.aa is False

    def test_conf_comma(self):
        data = j(['[sec1]', 'aa = [=COMMA] xxx1, xxx2, xxx3'])
        conf = fetch(data)
        assert conf.sec1.aa == ['xxx1', 'xxx2', 'xxx3']

    def test_conf_comma_indent(self):
        data = j(['[sec1]', 'aa = [=COMMA] xxx1, xxx2,', '    xxx3'])
        conf = fetch(data)
        assert conf.sec1.aa == ['xxx1', 'xxx2', 'xxx3']

    def test_conf_comma_newline(self):
        data = j(['[sec1]', 'aa = [=COMMA] xxx1, xxx2', '    xxx3'])
        conf = fetch(data)
        assert conf.sec1.aa == ['xxx1', 'xxx2\nxxx3']

    def test_conf_comma_blank(self):
        data = j(['[sec1]', 'aa = [=COMMA]'])
        conf = fetch(data)
        assert conf.sec1.aa == []

    def test_conf_line(self):
        data = j(['[sec1]',
            'aa = [=LINE]', '    xxx1', '    xxx2', '    xxx3'])
        conf = fetch(data)
        assert conf.sec1.aa == ['xxx1', 'xxx2', 'xxx3']

    def test_conf_line_comma(self):
        data = j(['[sec1]',
            'aa = [=LINE]', '    xxx1', '    xxx2', '    xxx3, xxx4'])
        conf = fetch(data)
        assert conf.sec1.aa == ['xxx1', 'xxx2', 'xxx3, xxx4']

    def test_conf_line_blank(self):
        data = j(['[sec1]', 'aa = [=LINE]'])
        conf = fetch(data)
        assert conf.sec1.aa == []

    def test_conf_line_multiblanks(self):
        data = j(['[sec1]', 'aa = [=LINE]', '    ', '    '])
        conf = fetch(data)
        assert conf.sec1.aa == []

    def test_conf_bar_comma(self):
        data = j(['[sec1]', 'aa = [=COMMA][=BAR] xxx1, xxx2, xxx3'])
        conf = fetch(data)
        assert conf.sec1.aa == 'xxx1|xxx2|xxx3'

    def test_conf_bar_comma_blank(self):
        data = j(['[sec1]', 'aa = [=COMMA][=BAR]'])
        conf = fetch(data)
        assert conf.sec1.aa == ''

    def test_conf_bar_comma_blank_spaces(self):
        data = j(['[sec1]', 'aa = [=COMMA] [=BAR]    '])
        conf = fetch(data)
        assert conf.sec1.aa == ''

    def test_conf_bar_line(self):
        data = j(['[sec1]', 'aa = [=LINE][=BAR] xxx1', '    xxx2', '    xxx3'])
        conf = fetch(data)
        assert conf.sec1.aa == 'xxx1|xxx2|xxx3'

    def test_conf_bar_line_blank(self):
        data = j(['[sec1]', 'aa = [=LINE][=BAR]'])
        conf = fetch(data)
        assert conf.sec1.aa == ''

    def test_conf_bar_line_blank_spaces(self):
        data = j(['[sec1]', 'aa = [=LINE] [=BAR]    '])
        conf = fetch(data)
        assert conf.sec1.aa == ''

    def test_conf_cmd(self):
        data = j(['[sec1]', 'aa = [=CMD] --aaa -b "ccc cc" ddd,dd'])
        conf = fetch(data)
        assert conf.sec1.aa == ['--aaa', '-b', 'ccc cc', 'ddd,dd']

    def test_conf_cmds(self):
        data = j(['[sec1]', 'aa = [=COMMA][=CMDS] ls *.txt, find . "aaa"'])
        conf = fetch(data)
        assert conf.sec1.aa == [['ls', '*.txt'], ['find', '.', 'aaa']]

    def test_conf_fmt(self):
        data = j(['[sec1]', 'aa = [=FMT] {USER}/data/my.css'])
        conf = fetch(data, fmts={'USER': '/home/john'})
        assert conf.sec1.aa == '/home/john/data/my.css'


class TestParseContexts:

    def test_ctx_default_bool(self):
        data = j(['[DEFAULT]', 'aa = [=BOOL] no', '[sec1]'])
        conf = fetch(data)
        assert conf.sec1.aa is False

    def test_ctx_default_bool_noop(self):
        data = j(['[DEFAULT]', 'aa = [=BOOL]', '[sec1]', 'aa = no'])
        conf = fetch(data)
        assert conf.sec1.aa is False

    def test_ctx_default_comma(self):
        data = j(['[DEFAULT]', 'aa = [=COMMA]', '[sec1]', 'aa = xxx1, xxx2, xxx3'])
        conf = fetch(data)
        assert conf.sec1.aa == ['xxx1', 'xxx2', 'xxx3']


class TestParseFunc:

    def test_func_newline(self):
        data = j(['[sec1]', 'aa = ', '    [=BOOL] no'])
        conf = fetch(data)
        assert conf.sec1.aa is False


# Just checking the library's behaviors.
class TestConfigParser:

    def test_allow_no_value(self):
        data = j(['[sec1]', 'aa = ', '    [=BOOL] no'])
        config = configparser.ConfigParser(allow_no_value=True)
        config.read_string(data)
        assert config['sec1']['aa'] == '\n[=BOOL] no'


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
        data = j(['[sec1]', 'aa = xxx'])
        args = self.get_args(['--aa', 'axxx'])
        conf = fetch(data, args=args)
        assert conf.sec1.aa == 'axxx'

    def test_args_and_conf_short(self):
        data = j(['[sec1]', 'aa = xxx'])
        args = self.get_args(['-a', 'axxx'])
        conf = fetch(data, args=args)
        assert conf.sec1.aa == 'axxx'

    def test_args_and_conf_none(self):
        data = j(['[sec1]', 'aa = xxx'])
        args = self.get_args([])
        conf = fetch(data, args=args)
        assert conf.sec1.aa == 'xxx'

    def test_args_and_conf_const(self):
        data = j(['[sec1]', 'cc = [=BOOL]'])
        args = self.get_args(['--cc'])
        conf = fetch(data, args=args)
        assert conf.sec1.cc is True

    def test_args_and_conf_const_false(self):
        data = j(['[sec1]', 'cc = [=BOOL] true'])
        args = self.get_args(['--no-cc'])
        conf = fetch(data, args=args)
        assert conf.sec1.cc is False

    def test_args_and_conf_dash(self):
        data = j(['[sec1]', 'ee_eee = xxx'])
        args = self.get_args(['-e', 'axxx'])
        conf = fetch(data, args=args)
        assert conf.sec1.ee_eee == 'axxx'


class CustomFunc(configfetch.Func):

    @configfetch.register
    def _custom(self, value):
        return 'test'


class TestCustomize:

    def test_customfunc(self):
        data = j(['[sec1]', 'aa = [=CUSTOM] xxx'])
        conf = fetch(data, Func=CustomFunc)
        assert conf.sec1.aa == 'test'


class TestDouble:

    def test_nooptionerror_nooptionerror(self):
        data = j(['[sec1]', 'aa = xxx'])
        conf1 = fetch(data)
        data = j(['[sec1]', 'aa = yyy'])
        conf2 = fetch(data)
        double = configfetch.Double(conf2.sec1, conf1.sec1)
        with pytest.raises(configfetch.NoOptionError):
            assert double.bb == 'zzz'

    def test_nooptionerror_blankvalue(self):
        data = j(['[sec1]', 'aa = xxx'])
        conf1 = fetch(data)
        data = j(['[sec1]', 'bb ='])
        conf2 = fetch(data)
        double = configfetch.Double(conf2.sec1, conf1.sec1)
        assert double.bb == ''

    def test_blankvalue_nooptionerror(self):
        data = j(['[sec1]', 'bb ='])
        conf1 = fetch(data)
        data = j(['[sec1]', 'aa = yyy'])
        conf2 = fetch(data)
        double = configfetch.Double(conf2.sec1, conf1.sec1)
        assert double.bb == ''

    def test_blankvalue_blankvalue(self):
        data = j(['[sec1]', 'bb ='])
        conf1 = fetch(data)
        data = j(['[sec1]', 'bb = [=COMMA]'])
        conf2 = fetch(data)
        double = configfetch.Double(conf2.sec1, conf1.sec1)
        assert double.bb == ''

    def test_plus(self):
        data = j(['[sec1]', 'aa = [=PLUS] xxx, yyy'])
        conf1 = fetch(data)
        data = j(['[sec1]', 'aa = [=PLUS] -yyy'])
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
