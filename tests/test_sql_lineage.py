from amu_governance.sql_lineage import extract_lineage_from_sql, lineage_from_sql, lineage_summary


def test_extract_simple_alias():
    sql = "SELECT c.CategoryName, c.Description FROM Categories c WHERE c.CategoryID = 1"
    steps = extract_lineage_from_sql(sql)
    assert len(steps) == 1
    assert steps[0]["table"] == "categories"
    assert set(steps[0]["columns"]) == {"categoryname", "description", "categoryid"}


def test_extract_multi_table_join():
    sql = """
        SELECT c.CategoryName, SUM(od.UnitPrice * od.Quantity) AS revenue
        FROM Categories c
        JOIN Products p ON c.CategoryID = p.CategoryID
        JOIN "Order Details" od ON p.ProductID = od.ProductID
        GROUP BY c.CategoryName
    """
    steps = extract_lineage_from_sql(sql)
    tables = {s["table"] for s in steps}
    assert tables == {"categories", "products", "order_details"}


def test_extract_handles_unparseable_sql_gracefully():
    assert extract_lineage_from_sql("this is not sql at all {{{") == []
    assert extract_lineage_from_sql("") == []


def test_lineage_from_sql_builds_lineage_object():
    sql = "SELECT e.HomePhone, e.Title FROM Employees e"
    lineage = lineage_from_sql(sql, filter_logic="all employees")
    assert len(lineage.steps) == 1
    assert lineage.steps[0].table == "employees"
    assert set(lineage.steps[0].columns_used) == {"homephone", "title"}
    assert lineage.filter_logic == "all employees"


def test_lineage_summary_formats_readably():
    steps = [{"table": "orders", "columns": ["orderid", "shipcountry"]}]
    assert "orders" in lineage_summary(steps)
    assert lineage_summary([]) == "(no lineage extracted)"
