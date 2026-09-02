"""Tests for the ROPA data model, dashboard filters, and exports.

Covers the parts of this app where a silent regression would matter
most: the risk-triage rule (`ProcessingActivity.is_high_risk`), the
dashboard's filter/search query logic, and the export endpoints
actually producing well-formed CSV/PDF output.
"""

import csv
import io

from django.test import Client, TestCase
from django.urls import reverse

from .models import (
    DataCategory,
    DataRecipient,
    LegalBasis,
    ProcessingActivity,
    RetentionPeriod,
)


def make_activity(
    name="Test Activity",
    categories=None,
    legal_basis=None,
    retention_period=None,
    recipients=None,
):
    activity = ProcessingActivity.objects.create(
        name=name,
        department="Test Department",
        purpose="Testing.",
        legal_basis=legal_basis,
        retention_period=retention_period,
    )
    if categories:
        activity.data_categories.set(categories)
    if recipients:
        activity.recipients.set(recipients)
    return activity


class RiskFlagTests(TestCase):
    """`is_high_risk` should fire only for sensitive data with a
    documented-data gap, and never for non-sensitive data regardless
    of how incomplete the record is."""

    def setUp(self):
        self.sensitive = DataCategory.objects.create(name="Health Data", is_sensitive=True)
        self.ordinary = DataCategory.objects.create(name="Contact Info", is_sensitive=False)
        self.basis = LegalBasis.objects.create(name="Consent")
        self.retention = RetentionPeriod.objects.create(
            duration_label="1 year", justification="Test."
        )

    def test_sensitive_data_missing_both_fields_is_high_risk(self):
        activity = make_activity(categories=[self.sensitive])
        self.assertTrue(activity.is_high_risk)
        self.assertEqual(len(activity.risk_reasons), 2)

    def test_sensitive_data_missing_legal_basis_only_is_high_risk(self):
        activity = make_activity(
            categories=[self.sensitive], retention_period=self.retention
        )
        self.assertTrue(activity.is_high_risk)
        self.assertEqual(len(activity.risk_reasons), 1)

    def test_sensitive_data_missing_retention_only_is_high_risk(self):
        activity = make_activity(categories=[self.sensitive], legal_basis=self.basis)
        self.assertTrue(activity.is_high_risk)
        self.assertEqual(len(activity.risk_reasons), 1)

    def test_sensitive_data_with_both_fields_is_not_high_risk(self):
        activity = make_activity(
            categories=[self.sensitive],
            legal_basis=self.basis,
            retention_period=self.retention,
        )
        self.assertFalse(activity.is_high_risk)
        self.assertEqual(activity.risk_reasons, [])

    def test_non_sensitive_data_is_never_high_risk_even_if_incomplete(self):
        activity = make_activity(categories=[self.ordinary])
        self.assertFalse(activity.is_high_risk)
        self.assertEqual(activity.risk_reasons, [])

    def test_activity_with_no_categories_is_not_high_risk(self):
        activity = make_activity()
        self.assertFalse(activity.involves_sensitive_data)
        self.assertFalse(activity.is_high_risk)


class InternationalTransferTests(TestCase):
    def test_flagged_when_any_recipient_is_international(self):
        domestic = DataRecipient.objects.create(name="Local Team", is_international_transfer=False)
        overseas = DataRecipient.objects.create(name="Overseas Vendor", is_international_transfer=True)
        activity = make_activity(recipients=[domestic, overseas])
        self.assertTrue(activity.involves_international_transfer)

    def test_not_flagged_when_no_recipient_is_international(self):
        domestic = DataRecipient.objects.create(name="Local Team", is_international_transfer=False)
        activity = make_activity(recipients=[domestic])
        self.assertFalse(activity.involves_international_transfer)

    def test_not_flagged_with_no_recipients(self):
        activity = make_activity()
        self.assertFalse(activity.involves_international_transfer)


class DashboardFilterTests(TestCase):
    """Exercises the query-param filtering in views._filtered_activities
    through the actual dashboard endpoint, the way a browser would hit it."""

    def setUp(self):
        self.client = Client()
        self.category_a = DataCategory.objects.create(name="Category A")
        self.category_b = DataCategory.objects.create(name="Category B")
        self.basis_consent = LegalBasis.objects.create(name="Consent")
        self.basis_contract = LegalBasis.objects.create(name="Contract Necessity")
        self.domestic = DataRecipient.objects.create(name="Domestic Team", is_international_transfer=False)
        self.overseas = DataRecipient.objects.create(name="Overseas Vendor", is_international_transfer=True)

        self.activity_a = make_activity(
            name="Alpha Activity",
            categories=[self.category_a],
            legal_basis=self.basis_consent,
            recipients=[self.overseas],
        )
        self.activity_b = make_activity(
            name="Beta Activity",
            categories=[self.category_b],
            legal_basis=self.basis_contract,
            recipients=[self.domestic],
        )

    def test_dashboard_with_no_filters_shows_all(self):
        response = self.client.get(reverse("ropa:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["activities"]), 2)

    def test_filter_by_data_category(self):
        response = self.client.get(
            reverse("ropa:dashboard"), {"data_category": self.category_a.id}
        )
        activities = response.context["activities"]
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0], self.activity_a)

    def test_filter_by_legal_basis(self):
        response = self.client.get(
            reverse("ropa:dashboard"), {"legal_basis": self.basis_contract.id}
        )
        activities = response.context["activities"]
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0], self.activity_b)

    def test_filter_by_international_transfer_yes(self):
        response = self.client.get(reverse("ropa:dashboard"), {"international": "yes"})
        activities = response.context["activities"]
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0], self.activity_a)

    def test_filter_by_international_transfer_no(self):
        response = self.client.get(reverse("ropa:dashboard"), {"international": "no"})
        activities = response.context["activities"]
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0], self.activity_b)

    def test_search_matches_name(self):
        response = self.client.get(reverse("ropa:dashboard"), {"q": "Alpha"})
        activities = response.context["activities"]
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0], self.activity_a)

    def test_search_no_match_returns_empty(self):
        response = self.client.get(reverse("ropa:dashboard"), {"q": "Nonexistent"})
        self.assertEqual(len(response.context["activities"]), 0)


class ExportTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.sensitive = DataCategory.objects.create(name="Health Data", is_sensitive=True)
        make_activity(name="Exported Activity", categories=[self.sensitive])

    def test_csv_export_returns_valid_csv_with_expected_row(self):
        response = self.client.get(reverse("ropa:export_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

        content = response.content.decode("utf-8")
        rows = list(csv.reader(io.StringIO(content)))
        # Header row of the table lives after the title/date lines.
        header_row = next(r for r in rows if r and r[0] == "Activity")
        data_rows = rows[rows.index(header_row) + 1:]
        self.assertTrue(any(row and row[0] == "Exported Activity" for row in data_rows))

    def test_csv_export_respects_filters(self):
        DataCategory.objects.create(name="Unrelated Category")
        make_activity(name="Should Be Excluded")
        response = self.client.get(
            reverse("ropa:export_csv"), {"data_category": self.sensitive.id}
        )
        content = response.content.decode("utf-8")
        self.assertIn("Exported Activity", content)
        self.assertNotIn("Should Be Excluded", content)

    def test_pdf_export_returns_valid_pdf(self):
        response = self.client.get(reverse("ropa:export_pdf"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))
