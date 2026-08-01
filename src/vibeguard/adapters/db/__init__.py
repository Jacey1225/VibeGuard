"""Importing this package registers every ORM model on the shared `Base`.

SQLAlchemy declarative models register themselves on `Base.metadata` at
import time. Every model module beyond `models.py` must be imported
here too, or `Base.metadata` would be missing their tables anywhere
only `models` was imported directly (migrations, `create_all()` in
tests).
"""

from vibeguard.adapters.db import (  # noqa: F401
    finding_model,
    models,
    remediation_model,
    user_model,
)
