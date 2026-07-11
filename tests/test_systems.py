from amu_governance import AMU, Lineage, LineageStep
from amu_governance import LineageAwareSystem, NaiveMemorySystem, NoMemorySystem


def _sensitive_amu(department: str, epoch: int) -> AMU:
    lineage = Lineage(
        steps=(LineageStep("customers", ("customer_id", "income")),),
        filter_logic="income > 100000",
    )
    return AMU("high_value_segment", 12.0, department, lineage, epoch)


def _safe_amu(department: str, epoch: int) -> AMU:
    lineage = Lineage(
        steps=(LineageStep("transactions", ("txn_id", "amount")),),
        filter_logic="all transactions",
    )
    return AMU("order_volume", 999.0, department, lineage, epoch)


def test_no_memory_system_never_leaks_never_reuses(policy):
    system = NoMemorySystem(policy)
    fin_amu = _sensitive_amu("Finance", 0)
    system.write(fin_amu)
    result = system.request("high_value_segment", "Marketing", _sensitive_amu("Marketing", 1))
    assert result.served
    assert not result.leaked
    assert not result.reused


def test_naive_memory_system_leaks_sensitive_data(policy):
    system = NaiveMemorySystem(policy)
    fin_amu = _sensitive_amu("Finance", 0)
    system.write(fin_amu)

    result = system.request("high_value_segment", "Marketing", _sensitive_amu("Marketing", 1))
    assert result.reused
    assert result.leaked  # income touched, Marketing not permitted -> leak


def test_naive_memory_system_does_not_leak_safe_metric(policy):
    system = NaiveMemorySystem(policy)
    system.write(_safe_amu("Finance", 0))

    result = system.request("order_volume", "Marketing", _safe_amu("Marketing", 1))
    assert result.reused
    assert not result.leaked


def test_lineage_aware_system_blocks_sensitive_retrieval(policy):
    system = LineageAwareSystem(policy)
    system.write(_sensitive_amu("Finance", 0))

    result = system.request("high_value_segment", "Marketing", _sensitive_amu("Marketing", 1))
    assert not result.leaked          # never leaks, by construction
    assert not result.reused          # blocked -> falls back to fresh compute
    assert result.blocked


def test_lineage_aware_system_serves_safe_metric_from_memory(policy):
    system = LineageAwareSystem(policy)
    system.write(_safe_amu("Finance", 0))

    result = system.request("order_volume", "Marketing", _safe_amu("Marketing", 1))
    assert result.reused
    assert not result.blocked
    assert not result.leaked


def test_lineage_aware_system_flags_definition_conflict(policy):
    system = LineageAwareSystem(policy)
    fin_amu = _sensitive_amu("Finance", 0)
    system.write(fin_amu)

    # Marketing writes its own, differently-derived AMU under the same metric_name.
    mkt_lineage = Lineage(
        steps=(LineageStep("transactions", ("customer_id", "amount")),),
        filter_logic="amount > 10000 (no income)",
    )
    mkt_amu = AMU("high_value_segment", 5.0, "Marketing", mkt_lineage, epoch=1)

    conflict = system.write(mkt_amu)
    assert conflict is True
    assert fin_amu.definition_hash != mkt_amu.definition_hash


def test_lineage_aware_system_no_false_conflict_same_department(policy):
    system = LineageAwareSystem(policy)
    system.write(_sensitive_amu("Finance", 0))
    # Same department writing again should never be flagged as a conflict
    # with its own earlier definition.
    conflict = system.write(_sensitive_amu("Finance", 1))
    assert conflict is False


def test_unknown_department_is_denied_by_default(policy):
    """Fail closed: a department with no entry in the policy gets zero
    permitted columns, so any sensitive AMU is blocked, never leaked."""
    system = LineageAwareSystem(policy)
    system.write(_sensitive_amu("Finance", 0))
    result = system.request("high_value_segment", "UnknownDept", _sensitive_amu("UnknownDept", 1))
    assert result.blocked
    assert not result.leaked
