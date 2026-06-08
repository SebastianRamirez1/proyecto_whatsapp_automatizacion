"""Session-scoped fixtures shared by all tests.

The app uses Alembic for production migrations, but running `alembic upgrade head`
in CI adds complexity and depends on the migration history being correct.
For the test suite it is simpler and more robust to let SQLAlchemy create the
schema directly from the model definitions before any test runs.
"""
import pytest

from app.db.session import Base, engine

# Import every model so their table definitions are registered on Base.metadata
# before create_all is called.  Without these imports the metadata is empty.
import app.models.client  # noqa: F401
import app.models.order  # noqa: F401
import app.models.order_item  # noqa: F401


@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    """Create all tables once for the whole test session, drop them on teardown."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
