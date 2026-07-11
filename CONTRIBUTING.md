# Contributing

Bug reports, feature requests, and pull requests are welcome via
[GitHub Issues](https://github.com/sangaraju1988/amu-governance/issues) and
pull requests.

## Development setup

```bash
git clone https://github.com/sangaraju1988/amu-governance.git
cd amu-governance
pip install -e ".[dev]"
pytest
```

## Guidelines

- Keep `amu_governance` domain-agnostic: sensitivity and permissions belong
  in a `GovernancePolicy`, not hardcoded into the model or system classes.
- Add or update tests for any behavioral change (`tests/`).
- Run `pytest` before opening a pull request.
- Match the existing docstring style — every public function/class should
  explain *why*, not just *what*.

## Reporting security issues

If you find a case where `LineageAwareSystem` fails to block a retrieval it
should have blocked, please open an issue and mark it clearly — that is a
correctness bug in the core safety guarantee, not a feature request.
