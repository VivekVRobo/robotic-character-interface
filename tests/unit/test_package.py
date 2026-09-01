from rci import __version__


def test_package_has_version() -> None:
    assert __version__ == "0.1.0-dev0"
