"""Immutable initial schema snapshot for the prototype."""

from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def snapshot():
    spec = spec_from_file_location(
        "schema_v1", Path(__file__).parents[1] / "schema_v1.py"
    )
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.metadata


def upgrade():
    snapshot().create_all(op.get_bind())


def downgrade():
    raise RuntimeError(
        "Destructive downgrade is disabled; restore a reviewed backup instead."
    )
