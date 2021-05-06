import os
import subprocess
import sys
import pytest
from pathlib import Path
from tempenv import TemporaryEnvironment
from test_pyenv import TestPyenvBase
from test_pyenv_helpers import TempPyEnv


class TestPyenvFeatureExec(TestPyenvBase):
    _temp_env = None
    _temp_path = None
    ctx = None

    """
    We do not have any python version installed.
    But we prepend the path with sys.executable dir.
    And we remote fake python.exe (empty file generated) to ensure sys.executable is found and used.
    This method allows us to execute python.exe.
    But it cannot be used to play with many python versions.
    """
    @classmethod
    def setup_class(cls):
        settings = {'versions': ['3.7.7'], 'global_ver': '3.7.7'}
        cls._temp_env = TempPyEnv(settings)
        cls.ctx = cls._temp_env.context
        cls._temp_path = TemporaryEnvironment({"PATH": f"{os.path.dirname(sys.executable)};"
                                                       f"{str(Path(cls.ctx.pyenv_path, 'bin'))};"
                                                       f"{str(Path(cls.ctx.pyenv_path, 'shims'))};"
                                                       f"{os.environ['PATH']}"})
        cls._temp_path.__enter__()
        cls.ctx.pyenv('rehash')
        os.unlink(str(Path(cls.ctx.pyenv_path, r'versions\3.7.7\python.exe')))

    @classmethod
    def teardown_class(cls):
        cls._temp_path.__exit__(None)
        cls._temp_env.cleanup()

    @pytest.mark.parametrize(
        "command",
        [
            lambda path: [str(path / "bin" / "pyenv.bat"), "exec", "python"],
            lambda path: [str(path / "shims" / "python.bat")],
        ],
        ids=["pyenv exec", "python shim"],
    )
    @pytest.mark.parametrize(
        "arg",
        [
            "Hello",
            "Hello World",
            "Hello 'World'",
            'Hello "World"',  # " is escaped as \" by python
            "Hello %World%",
            # "Hello %22World%22",
            "Hello !World!",
            "Hello #World#",
            "Hello World'",
            'Hello World"',
            "Hello ''World'",
            'Hello ""World"',
        ],
        ids=[
            "One Word",
            "Two Words",
            "Single Quote",
            "Double Quote",
            "Percentage",
            # "Escaped",
            "Exclamation Mark",
            "Pound",
            "One Single Quote",
            "One Double Quote",
            "Imbalance Single Quote",
            "Imbalance Double Quote",
        ]
    )
    def test_exec_arg(self, setup, command, arg):
        with TemporaryEnvironment({'World': 'Earth'}):
            args = [*command(self.__class__.ctx.pyenv_path), "-c", "import sys; print(sys.argv[1])", arg]
            result = subprocess.run(args, capture_output=True, encoding="utf8")
            # \x0c: generated by cls in cmd AutoRun
            stdout = result.stdout.strip("\r\n\x0c")
            # " is escaped as \" by python, so we unescape it here
            stdout = stdout.replace('\\', '"')
            stderr = result.stderr.strip()
            if stderr != "":
                print(f'stderr: {stderr}')
            assert stdout == arg.replace('%World%', 'Earth')

    @pytest.mark.parametrize(
        "args",
        [
            ["--help", "exec"],
            ["help", "exec"],
            ["exec", "--help"],
        ],
        ids=[
            "--help exec",
            "help exec",
            "exec --help",
        ]
    )
    def test_exec_help(self, setup, args):
        args = [str(self.__class__.ctx.pyenv_path / "bin" / "pyenv.bat"), *args]
        result = subprocess.run(args, capture_output=True, encoding="utf8")
        # \x0c: generated by cls in cmd AutoRun
        stdout = result.stdout.strip("\r\n\x0c")
        assert "\r\n".join(stdout.splitlines()[:1]) == pyenv_exec_help()

    def test_path_not_updated(self, setup):
        python = str(self.__class__.ctx.pyenv_path / "shims" / "python.bat")
        tmp_bat = str(Path(self.__class__.ctx.local_path, "tmp.bat"))
        with open(tmp_bat, "w") as f:
            # must chain commands because env var is lost when cmd ends
            print(f'@echo %PATH%', file=f)
            print(f'@call {python} -V>nul', file=f)
            print(f'@echo %PATH%', file=f)
        args = ["call", tmp_bat]
        result = subprocess.run(args, shell=True, capture_output=True, encoding="utf8")
        # \x0c: generated by cls in cmd AutoRun
        stdout = result.stdout.strip("\r\n\x0c").splitlines()
        assert stdout[0] == stdout[1]


def pyenv_exec_help():
    return "Usage: pyenv exec <command> [arg1 arg2...]"
