import sys
import os


sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../src/cloud_functions")
    ),
)

from main import add


def test_add():
    result = add(2, 3)
    assert result == 5, f"Expected 5, but got {result}"
