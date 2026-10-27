import copy
import json
from pathlib import Path

import pytest

from demo_builder.validation import ValidationError, validate_business, validate_prospect


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def read_fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_fictional_business_fixture_passes_demo_validation():
    assert validate_business(read_fixture("fictional-business.json"), demo_mode=True)["fixture_type"] == "fictional"


def test_demo_mode_rejects_non_reserved_url():
    data = copy.deepcopy(read_fixture("fictional-business.json"))
    data["public_url"] = "https://business.invalid"
    with pytest.raises(ValidationError, match="example.com"):
        validate_business(data, demo_mode=True)


def test_demo_mode_rejects_non_fixture_phone():
    data = copy.deepcopy(read_fixture("fictional-business.json"))
    data["phone"] = "+12120000000"
    with pytest.raises(ValidationError, match="555"):
        validate_business(data, demo_mode=True)


def test_fictional_prospect_fixture_passes_demo_validation():
    assert validate_prospect(read_fixture("fictional-prospect.json"), demo_mode=True)["first_name"] == "Jamie"
