import unittest
from unittest.mock import Mock, patch

from sync_tcg_to_monarch import get_tcgcollector_portfolio_value, validate_balance_change


class PortfolioValueTests(unittest.TestCase):
    def test_extracts_collection_value(self):
        response = Mock()
        response.text = "<div>Collection Value: $1,234.56</div>"

        with patch("sync_tcg_to_monarch.requests.get", return_value=response):
            value = get_tcgcollector_portfolio_value("https://example.test/dashboard")

        self.assertEqual(value, 1234.56)


class BalanceValidationTests(unittest.TestCase):
    def test_accepts_change_within_limit(self):
        validate_balance_change(1000.0, 1200.0, 200.0)

    def test_rejects_change_over_limit(self):
        with self.assertRaisesRegex(ValueError, "MAX_BALANCE_CHANGE"):
            validate_balance_change(1000.0, 1201.0, 200.0)

    def test_rejects_non_finite_values(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            validate_balance_change(1000.0, float("inf"), 200.0)

    def test_rejects_negative_values(self):
        with self.assertRaisesRegex(ValueError, "negative"):
            validate_balance_change(1000.0, -1.0, 200.0)


if __name__ == "__main__":
    unittest.main()