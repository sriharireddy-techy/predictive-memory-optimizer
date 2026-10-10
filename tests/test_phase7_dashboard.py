import pytest
import pandas as pd
from src.dashboard.components import format_timestamp, get_pressure_color

def test_format_timestamp():
    ts = 1699999999.0
    # Just check it returns a string in correct format (H:M:S)
    res = format_timestamp(ts)
    assert isinstance(res, str)
    assert len(res.split(':')) == 3

def test_get_pressure_color():
    assert get_pressure_color("NORMAL") == "#00FFFF"
    assert get_pressure_color("CRITICAL") == "#F44336"
    assert get_pressure_color("UNKNOWN") == "white"
