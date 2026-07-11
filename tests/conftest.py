import pytest

from amu_governance import GovernancePolicy


@pytest.fixture
def policy() -> GovernancePolicy:
    return GovernancePolicy(
        sensitive_columns={"ssn", "email", "income"},
        department_permissions={
            "Finance": {"ssn", "income", "email", "customer_id", "region",
                        "txn_id", "amount"},
            "Marketing": {"customer_id", "region", "txn_id", "amount"},
            "Support": {"customer_id", "region"},
        },
    )
