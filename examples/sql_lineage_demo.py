"""
Automatic lineage extraction from executed SQL, no agent self-reporting.

Run:  python examples/sql_lineage_demo.py
"""

from amu_governance.sql_lineage import extract_lineage_from_sql, lineage_summary

QUERIES = {
    "Simple alias": "SELECT c.CategoryName, c.Description FROM Categories c WHERE c.CategoryID = 1",
    "Multi-table JOIN": """
        SELECT c.CategoryName, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) AS revenue
        FROM Categories c
        JOIN Products p ON c.CategoryID = p.CategoryID
        JOIN "Order Details" od ON p.ProductID = od.ProductID
        GROUP BY c.CategoryName
    """,
    "Sensitive column": "SELECT e.FirstName, e.LastName, e.HomePhone FROM Employees e",
    "Subquery": """
        SELECT p.ProductName, p.UnitPrice FROM Products p
        WHERE p.UnitPrice > (SELECT AVG(UnitPrice) FROM Products)
    """,
}

if __name__ == "__main__":
    for name, sql in QUERIES.items():
        steps = extract_lineage_from_sql(sql)
        print(f"[{name}]\n  {lineage_summary(steps)}\n")
