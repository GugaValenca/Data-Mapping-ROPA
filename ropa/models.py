"""
Data model for the Data-Mapping-ROPA tool.

This app models a Record of Processing Activities (ROPA) the way a privacy
team actually maintains one: structured, relational records instead of a
static spreadsheet or Word document. Each ProcessingActivity is the row a
regulator or auditor would expect to see in a ROPA, built from reusable
building blocks (categories, legal bases, recipients, retention periods)
so the same reference data doesn't get retyped for every activity.

IMPORTANT — legal disclaimer for anyone reviewing this code:
This is a portfolio project built around a fictional e-commerce company.
Business scenarios, department names, and vendor names are invented for
demonstration purposes. Retention periods and legal-basis labels are
illustrative placeholders, NOT legal advice and NOT asserted to be
correct under GDPR, LGPD, CCPA, or any other law. Anywhere a real
retention period or legal threshold would need to be sourced from an
actual statute or regulator guidance, see the
`# TODO: VERIFY legal retention standard against official source`
comments below and in ropa/management/commands/seed_ropa.py.
"""

from django.db import models


class DataCategory(models.Model):
    """A category of personal data collected or processed (e.g. contact
    info, payment info, browsing behavior, precise location).

    `is_sensitive` flags data the privacy team has classified as higher
    risk (e.g. health, government ID numbers, precise geolocation) and
    therefore warranting a clearly documented legal basis and retention
    period. This is an internal risk-classification flag for this tool's
    triage feature, not a citation to any specific statute's definition
    of "special category" or "sensitive" data.
    """

    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_sensitive = models.BooleanField(
        default=False,
        help_text=(
            "Internal risk classification: check this if the category "
            "warrants extra care (e.g. health, government ID, precise "
            "location), not a citation to a specific legal definition."
        ),
    )

    class Meta:
        verbose_name_plural = "Data categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class LegalBasis(models.Model):
    """A legal basis for processing (e.g. Consent, Contract Necessity,
    Legitimate Interest, Legal Obligation), reusable across activities."""

    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Legal bases"
        ordering = ["name"]

    def __str__(self):
        return self.name


class DataRecipient(models.Model):
    """An internal team or third party that receives/accesses the data."""

    class RecipientType(models.TextChoices):
        INTERNAL = "internal", "Internal team"
        THIRD_PARTY = "third_party", "Third party / vendor"

    name = models.CharField(max_length=150)
    recipient_type = models.CharField(
        max_length=20, choices=RecipientType.choices, default=RecipientType.INTERNAL
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        help_text="Where this recipient is located or processes the data.",
    )
    is_international_transfer = models.BooleanField(
        default=False,
        help_text="Check if sharing with this recipient involves an international/cross-border data transfer.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        label = dict(self.RecipientType.choices).get(self.recipient_type, "")
        return f"{self.name} ({label})"


class RetentionPeriod(models.Model):
    """How long data is kept for a given activity, and why.

    # TODO: VERIFY legal retention standard against official source.
    The `duration_label` values seeded into this tool are illustrative
    business placeholders, not confirmed legal minimums/maximums. Before
    using this tool's output for a real company, each retention period
    must be checked against the actual statute, regulation, or regulator
    guidance that applies (e.g. tax record-keeping law, GDPR storage
    limitation guidance, LGPD Art. 15/16 deletion triggers, CCPA/CPRA
    retention disclosure rules) and updated accordingly.
    """

    duration_label = models.CharField(
        max_length=150,
        help_text='Human-readable duration, e.g. "24 months after account closure".',
    )
    justification = models.TextField(
        help_text="Business rationale for this retention period."
    )

    class Meta:
        ordering = ["duration_label"]

    def __str__(self):
        return self.duration_label


class ProcessingActivity(models.Model):
    """A single processing activity: the core row of the ROPA.

    `legal_basis` and `retention_period` are nullable on purpose, even
    though every real-world activity should have both clearly defined.
    Leaving them nullable lets this tool represent a privacy program's
    real, in-progress state — including the gaps — and its risk-flag
    feature (see `is_high_risk`) exists specifically to surface those
    gaps for follow-up instead of hiding them.
    """

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    department = models.CharField(max_length=120)
    purpose = models.TextField(help_text="Why this data is processed.")

    data_categories = models.ManyToManyField(DataCategory, related_name="activities")
    legal_basis = models.ForeignKey(
        LegalBasis,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activities",
    )
    recipients = models.ManyToManyField(
        DataRecipient, related_name="activities", blank=True
    )
    retention_period = models.ForeignKey(
        RetentionPeriod,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activities",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Processing activities"
        ordering = ["name"]

    def __str__(self):
        return self.name

    # --- Risk triage helpers -------------------------------------------------

    @property
    def involves_sensitive_data(self) -> bool:
        return self.data_categories.filter(is_sensitive=True).exists()

    @property
    def involves_international_transfer(self) -> bool:
        return self.recipients.filter(is_international_transfer=True).exists()

    @property
    def is_high_risk(self) -> bool:
        """Flag activities that combine sensitive data with an undocumented
        legal basis and/or retention period — i.e. exactly the gap a
        privacy program needs to close before an audit, not just a data
        entry problem."""
        return self.involves_sensitive_data and (
            self.legal_basis_id is None or self.retention_period_id is None
        )

    @property
    def risk_reasons(self) -> list[str]:
        """Short human-readable reasons behind is_high_risk, for display."""
        reasons = []
        if not self.involves_sensitive_data:
            return reasons
        if self.legal_basis_id is None:
            reasons.append("Sensitive data with no documented legal basis")
        if self.retention_period_id is None:
            reasons.append("Sensitive data with no documented retention period")
        return reasons
