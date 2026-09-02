"""Seed the database with realistic-but-fictional ROPA data for NimbusCart,
a fictional mid-size e-commerce company, so the dashboard, filters, exports,
and risk-flag feature all have something meaningful to show right away.

# TODO: VERIFY legal retention standard against official source.
Retention durations below (e.g. "7 years", "3 years") are illustrative
business placeholders chosen for a plausible-looking demo, NOT researched
legal minimums/maximums under GDPR, LGPD, CCPA, or tax law. Two activities
("Accessibility Accommodation Requests" and "Fraud Detection & Risk
Scoring") are seeded with a missing legal basis and/or retention period
on purpose, to demonstrate the dashboard's high-risk flag on data that a
real privacy team would still need to close the gap on.

Run with: python manage.py seed_ropa
Safe to re-run: it clears existing ROPA data first (--keep to skip that).
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from ropa.models import (
    DataCategory,
    DataRecipient,
    LegalBasis,
    ProcessingActivity,
    RetentionPeriod,
)


class Command(BaseCommand):
    help = (
        "Seed the database with sample ROPA data for NimbusCart (fictional e-commerce company)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep",
            action="store_true",
            help="Don't clear existing data before seeding.",
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            if not options["keep"]:
                self.stdout.write("Clearing existing ROPA data…")
                ProcessingActivity.objects.all().delete()
                DataRecipient.objects.all().delete()
                RetentionPeriod.objects.all().delete()
                LegalBasis.objects.all().delete()
                DataCategory.objects.all().delete()

            categories = self._seed_categories()
            legal_bases = self._seed_legal_bases()
            recipients = self._seed_recipients()
            retentions = self._seed_retentions()
            self._seed_activities(categories, legal_bases, recipients, retentions)

        self.stdout.write(self.style.SUCCESS("Seed data loaded."))

    # -- Reference data -------------------------------------------------

    def _seed_categories(self):
        data = [
            ("Contact Information", "Name, email, phone, mailing/shipping address.", False),
            (
                "Account Credentials",
                "Username and hashed password/authentication tokens.",
                False,
            ),
            (
                "Payment Card Data",
                "Tokenized card details and billing address, handled via a PCI-compliant processor.",
                False,
            ),
            ("Order History", "Past orders, items purchased, order value.", False),
            (
                "Browsing Behavior / Analytics Data",
                "Pages viewed, clicks, search queries, on-site behavior.",
                False,
            ),
            (
                "Device & Technical Data",
                "IP address, browser/device identifiers, cookies.",
                False,
            ),
            (
                "Marketing Preferences",
                "Opt-in/opt-out status, campaign engagement, communication preferences.",
                False,
            ),
            (
                "Customer Support Communications",
                "Content of support tickets, chat transcripts, call notes.",
                False,
            ),
            (
                "Precise Geolocation Data",
                "Delivery coordinates and real-time shipment tracking location.",
                True,
            ),
            (
                "Health / Accessibility Information",
                "Self-reported accessibility or mobility needs for service accommodation.",
                True,
            ),
            (
                "Government-Issued ID Numbers",
                "Tax ID or national ID numbers collected for high-value order or customs verification.",
                True,
            ),
        ]
        objs = {}
        for name, description, is_sensitive in data:
            objs[name] = DataCategory.objects.create(
                name=name, description=description, is_sensitive=is_sensitive
            )
        return objs

    def _seed_legal_bases(self):
        data = [
            (
                "Consent",
                "The customer has given clear, specific, opt-in permission for this processing.",
            ),
            (
                "Contract Necessity",
                "Processing is necessary to perform the contract with the customer (e.g. fulfilling an order).",
            ),
            (
                "Legitimate Interest",
                "Processing serves a legitimate business interest, balanced against customer privacy expectations.",
            ),
            (
                "Legal Obligation",
                "Processing is required to comply with a legal or regulatory obligation (e.g. tax reporting).",
            ),
        ]
        objs = {}
        for name, description in data:
            objs[name] = LegalBasis.objects.create(name=name, description=description)
        return objs

    def _seed_recipients(self):
        internal = DataRecipient.RecipientType.INTERNAL
        third_party = DataRecipient.RecipientType.THIRD_PARTY
        data = [
            (
                "IT & Security Team",
                internal,
                "United States",
                False,
                "Internal team; access for account security and fraud prevention.",
            ),
            (
                "Customer Support Team",
                internal,
                "United States",
                False,
                "Internal team handling tickets and chat.",
            ),
            (
                "Marketing Department",
                internal,
                "United States",
                False,
                "Internal team running campaigns and loyalty programs.",
            ),
            (
                "Finance Department",
                internal,
                "United States",
                False,
                "Internal team handling billing, tax, and financial reporting.",
            ),
            (
                "Global Payment Gateway Partner",
                third_party,
                "Ireland",
                True,
                "Third-party payment processor; EU processing center handles transaction data.",
            ),
            (
                "Email Marketing Platform (SaaS)",
                third_party,
                "Canada",
                True,
                "Third-party SaaS vendor sending campaign emails on NimbusCart's behalf.",
            ),
            (
                "Web Analytics Provider (SaaS)",
                third_party,
                "United States",
                True,
                "Third-party analytics SaaS; receives site-visitor data from EU/Brazil visitors into US-hosted infrastructure.",
            ),
            (
                "Customer Support Outsourcing Partner",
                third_party,
                "Philippines",
                True,
                "Contracted support desk handling overflow tickets.",
            ),
            (
                "Shipping Carrier Network",
                third_party,
                "Multiple (EU & Brazil logistics hubs)",
                True,
                "Regional logistics partners used for international deliveries.",
            ),
            (
                "Tax Authority Reporting Partner",
                third_party,
                "United States",
                False,
                "Domestic regulatory reporting intermediary.",
            ),
        ]
        objs = {}
        for name, rtype, country, intl, notes in data:
            objs[name] = DataRecipient.objects.create(
                name=name,
                recipient_type=rtype,
                country=country,
                is_international_transfer=intl,
                notes=notes,
            )
        return objs

    def _seed_retentions(self):
        # See module docstring: durations here are illustrative placeholders,
        # not confirmed against any specific statute.
        data = [
            (
                "Account lifetime + 3 years after closure",
                "Supports account recovery and dispute resolution after a customer closes their account. (Illustrative — verify against applicable law before production use.)",
            ),
            (
                "7 years for financial/tax record-keeping",
                "Aligned with common financial record-keeping practice for audit and tax purposes. (Illustrative — verify against applicable law before production use.)",
            ),
            (
                "Until consent withdrawn, plus 30-day processing buffer",
                "Marketing sends stop as soon as consent is withdrawn; buffer covers in-flight batch jobs. (Illustrative — verify against applicable law before production use.)",
            ),
            (
                "26 months from collection (cookie expiry)",
                "Matches standard analytics cookie lifetime; data is not kept beyond cookie expiry. (Illustrative — verify against applicable law before production use.)",
            ),
            (
                "3 years after ticket closure",
                "Retained to review service quality trends and handle follow-up complaints. (Illustrative — verify against applicable law before production use.)",
            ),
            (
                "3 years after delivery confirmation",
                "Covers delivery disputes and returns/warranty windows. (Illustrative — verify against applicable law before production use.)",
            ),
            (
                "Program membership duration + 2 years",
                "Supports rewards continuity and post-membership customer service. (Illustrative — verify against applicable law before production use.)",
            ),
        ]
        objs = {}
        for label, justification in data:
            objs[label] = RetentionPeriod.objects.create(
                duration_label=label, justification=justification
            )
        return objs

    # -- Processing activities -------------------------------------------

    def _seed_activities(self, cat, basis, rec, ret):
        activities = [
            {
                "name": "Customer Account Registration",
                "description": "Creating and maintaining customer accounts for the NimbusCart storefront.",
                "department": "Engineering / Customer Experience",
                "purpose": "Create and manage customer accounts to enable purchases, order tracking, and personalized service.",
                "data_categories": [cat["Contact Information"], cat["Account Credentials"]],
                "legal_basis": basis["Contract Necessity"],
                "recipients": [rec["IT & Security Team"]],
                "retention_period": ret["Account lifetime + 3 years after closure"],
            },
            {
                "name": "Payment Processing",
                "description": "Processing customer payments for orders placed on the storefront.",
                "department": "Finance",
                "purpose": "Process customer payments for orders and manage billing.",
                "data_categories": [cat["Payment Card Data"], cat["Contact Information"]],
                "legal_basis": basis["Contract Necessity"],
                "recipients": [rec["Global Payment Gateway Partner"]],
                "retention_period": ret["7 years for financial/tax record-keeping"],
            },
            {
                "name": "Marketing Email Campaigns",
                "description": "Sending promotional and product update emails to opted-in customers.",
                "department": "Marketing",
                "purpose": "Send promotional emails and personalized offers to customers who have opted in.",
                "data_categories": [
                    cat["Contact Information"],
                    cat["Marketing Preferences"],
                    cat["Browsing Behavior / Analytics Data"],
                ],
                "legal_basis": basis["Consent"],
                "recipients": [
                    rec["Email Marketing Platform (SaaS)"],
                    rec["Marketing Department"],
                ],
                "retention_period": ret[
                    "Until consent withdrawn, plus 30-day processing buffer"
                ],
            },
            {
                "name": "Website Analytics Cookies",
                "description": "Measuring site traffic and usage patterns to improve UX and recommendations.",
                "department": "Marketing / IT",
                "purpose": "Analyze website traffic and on-site behavior to improve user experience and product recommendations.",
                "data_categories": [
                    cat["Browsing Behavior / Analytics Data"],
                    cat["Device & Technical Data"],
                ],
                "legal_basis": basis["Consent"],
                "recipients": [rec["Web Analytics Provider (SaaS)"]],
                "retention_period": ret["26 months from collection (cookie expiry)"],
            },
            {
                "name": "Customer Support Tickets",
                "description": "Handling customer inquiries, complaints, and support requests across channels.",
                "department": "Customer Support",
                "purpose": "Respond to and resolve customer inquiries, complaints, and support requests.",
                "data_categories": [
                    cat["Contact Information"],
                    cat["Customer Support Communications"],
                    cat["Order History"],
                ],
                "legal_basis": basis["Contract Necessity"],
                "recipients": [
                    rec["Customer Support Team"],
                    rec["Customer Support Outsourcing Partner"],
                ],
                "retention_period": ret["3 years after ticket closure"],
            },
            {
                "name": "Order Fulfillment & Shipping",
                "description": "Fulfilling orders and coordinating delivery with logistics partners.",
                "department": "Logistics / Operations",
                "purpose": "Fulfill and ship customer orders, coordinate with carriers, and provide delivery tracking.",
                "data_categories": [
                    cat["Contact Information"],
                    cat["Order History"],
                    cat["Precise Geolocation Data"],
                ],
                "legal_basis": basis["Contract Necessity"],
                "recipients": [rec["Shipping Carrier Network"]],
                "retention_period": ret["3 years after delivery confirmation"],
            },
            {
                "name": "Accessibility Accommodation Requests",
                "description": "Capturing customer-reported accessibility needs to tailor delivery and support.",
                "department": "Customer Experience",
                "purpose": "Capture customer accessibility needs (e.g. mobility assistance) to tailor delivery and in-store service.",
                "data_categories": [cat["Health / Accessibility Information"]],
                "legal_basis": None,  # Intentional gap — demonstrates the risk flag.
                "recipients": [rec["Customer Support Team"]],
                "retention_period": None,  # Intentional gap — demonstrates the risk flag.
            },
            {
                "name": "Fraud Detection & Risk Scoring",
                "description": "Screening transactions and account activity for fraud and account takeover risk.",
                "department": "Trust & Safety / Security",
                "purpose": "Detect and prevent fraudulent transactions and account takeovers using behavioral and device signals.",
                "data_categories": [
                    cat["Device & Technical Data"],
                    cat["Browsing Behavior / Analytics Data"],
                    cat["Government-Issued ID Numbers"],
                ],
                "legal_basis": basis["Legitimate Interest"],
                "recipients": [rec["IT & Security Team"]],
                "retention_period": None,  # Intentional gap — has a legal basis but no defined retention.
            },
            {
                "name": "Tax & Financial Reporting",
                "description": "Meeting tax reporting obligations and keeping financial records for audits.",
                "department": "Finance",
                "purpose": "Comply with tax reporting obligations and maintain financial records for regulatory audits.",
                "data_categories": [
                    cat["Payment Card Data"],
                    cat["Government-Issued ID Numbers"],
                ],
                "legal_basis": basis["Legal Obligation"],
                "recipients": [
                    rec["Finance Department"],
                    rec["Tax Authority Reporting Partner"],
                ],
                "retention_period": ret["7 years for financial/tax record-keeping"],
            },
            {
                "name": "Customer Loyalty & Rewards Program",
                "description": "Managing loyalty points, redemptions, and member-only offers.",
                "department": "Marketing",
                "purpose": "Manage loyalty points, rewards redemption, and personalized offers for program members.",
                "data_categories": [
                    cat["Contact Information"],
                    cat["Order History"],
                    cat["Marketing Preferences"],
                ],
                "legal_basis": basis["Consent"],
                "recipients": [rec["Marketing Department"]],
                "retention_period": ret["Program membership duration + 2 years"],
            },
        ]

        for item in activities:
            data_categories = item.pop("data_categories")
            recipients = item.pop("recipients")
            activity = ProcessingActivity.objects.create(**item)
            activity.data_categories.set(data_categories)
            activity.recipients.set(recipients)

        self.stdout.write(f"Created {len(activities)} processing activities.")
