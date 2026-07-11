from amu_governance import AMU, Lineage, LineageStep


def test_lineage_step_sensitive_columns(policy):
    step = LineageStep("customers", ("customer_id", "income", "region"))
    assert step.sensitive_columns(policy) == {"income"}


def test_lineage_all_columns_union_across_steps(policy):
    lineage = Lineage(
        steps=(
            LineageStep("customers", ("customer_id", "income")),
            LineageStep("transactions", ("txn_id", "amount")),
        ),
        filter_logic="income > 100000",
    )
    assert lineage.all_columns() == {"customer_id", "income", "txn_id", "amount"}
    assert lineage.sensitive_columns(policy) == {"income"}


def test_definition_hash_is_deterministic_and_order_independent():
    lineage_a = Lineage(
        steps=(
            LineageStep("customers", ("customer_id", "income")),
            LineageStep("transactions", ("amount", "txn_id")),
        ),
        filter_logic="income > 100000",
    )
    lineage_b = Lineage(
        steps=(
            LineageStep("transactions", ("txn_id", "amount")),
            LineageStep("customers", ("income", "customer_id")),
        ),
        filter_logic="income > 100000",
    )
    assert lineage_a.definition_hash() == lineage_b.definition_hash()


def test_definition_hash_changes_with_filter_logic():
    steps = (LineageStep("transactions", ("txn_id", "amount")),)
    h1 = Lineage(steps=steps, filter_logic="amount > 100").definition_hash()
    h2 = Lineage(steps=steps, filter_logic="amount > 200").definition_hash()
    assert h1 != h2


def test_amu_sensitivity_tags_and_definition_hash(policy):
    lineage = Lineage(
        steps=(LineageStep("customers", ("customer_id", "income")),),
        filter_logic="income > 100000",
    )
    amu = AMU(
        metric_name="high_value_segment",
        value=42.0,
        owner_department="Finance",
        lineage=lineage,
        epoch=0,
    )
    assert amu.sensitivity_tags(policy) == {"income"}
    assert amu.definition_hash == lineage.definition_hash()


def test_amu_with_no_sensitive_columns_has_empty_tags(policy):
    lineage = Lineage(
        steps=(LineageStep("transactions", ("txn_id", "amount")),),
        filter_logic="all transactions",
    )
    amu = AMU("order_volume", 100.0, "Finance", lineage, epoch=0)
    assert amu.sensitivity_tags(policy) == set()
