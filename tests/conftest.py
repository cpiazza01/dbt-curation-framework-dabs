import pytest
from jinja2 import Environment, PackageLoader


@pytest.fixture
def jinja_env():
    return Environment(
        loader=PackageLoader("dbt_curation_framework", "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
