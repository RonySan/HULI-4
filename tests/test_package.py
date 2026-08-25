from huli import __app_name__, __version__


def test_package_identity() -> None:
    assert __app_name__ == "Huli"
    assert __version__ == "4.0.0-alpha.4"
