import json
import pickle

import pytest
from margrete_rpc.chart.notes import (
    AirDirection,
    ColorValue,
    ExtapDirection,
    FlickDirection,
    JointKind,
)


@pytest.mark.parametrize(
    "enum_type", [AirDirection, ColorValue, ExtapDirection, FlickDirection, JointKind]
)
def test_string_enum_behavior_across_python_versions(enum_type):
    for member in enum_type:
        value = member.value
        assert isinstance(member, str)
        assert member == value
        assert hash(member) == hash(value)
        assert str(member) == value
        assert f"{member}" == value
        assert format(member, ">20") == format(value, ">20")
        assert repr(member) == f"<{enum_type.__name__}.{member.name}: {value!r}>"
        assert enum_type(value) is member
        assert json.loads(json.dumps({"value": member})) == {"value": value}
        assert pickle.loads(pickle.dumps(member)) is member
