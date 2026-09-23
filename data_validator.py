"""Product Data Validator for 4GMC.

Validates generated product titles and descriptions against ProductSource verified attributes.
Ensures no unverified technical claims (voltage, wattage, RPM, battery capacity, HEPA, filtration, etc.)
are invented or present in generated copy unless backed by source evidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from product_source import ProductSource, TECHNICAL_ATTRIBUTE_KEYS, ATTRIBUTE_PATTERNS


@dataclass
class ValidationResult:
    passed: bool
    title: str
    description: str
    verified_claims: list[str] = field(default_factory=list)
    stripped_claims: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "title": self.title,
            "description": self.description,
            "verified_claims": self.verified_claims,
            "stripped_claims": self.stripped_claims,
            "errors": self.errors,
        }


class ProductDataValidator:
    """Validates marketing copy against ProductSource factual evidence."""

    @staticmethod
    def validate_and_clean(
        title: str,
        description: str,
        source: ProductSource,
        marketing_model_name: str = "",
    ) -> ValidationResult:
        clean_title = title.strip()
        clean_desc = description.strip()

        verified_claims: list[str] = []
        stripped_claims: list[str] = []
        errors: list[str] = []

        full_generated_text = f"{clean_title} {clean_desc}"

        # Check all technical attribute pattern categories
        for attr_key, patterns in ATTRIBUTE_PATTERNS.items():
            for pat in patterns:
                matches = re.finditer(pat, full_generated_text, re.IGNORECASE)
                for match in matches:
                    found_str = match.group(0).strip()
                    # Check if this attribute is verified in ProductSource
                    verified_attr = source.verified_attributes.get(attr_key)
                    if verified_attr:
                        # Verified in source
                        claim_info = f"{attr_key}: {found_str} (Verified)"
                        if claim_info not in verified_claims:
                            verified_claims.append(claim_info)
                    else:
                        # Unverified claim detected in AI generated copy -> Strip it!
                        stripped_claims.append(f"{attr_key}: {found_str}")
                        # Remove the unverified claim from title and description
                        clean_title = re.sub(re.escape(found_str), "", clean_title, flags=re.IGNORECASE)
                        clean_desc = re.sub(re.escape(found_str), "", clean_desc, flags=re.IGNORECASE)

        # Cleanup extra whitespace resulting from stripping
        clean_title = re.sub(r"\s+", " ", clean_title).strip()
        clean_desc = re.sub(r"\s+", " ", clean_desc).strip()
        clean_desc = re.sub(r"\n\s*\n", "\n\n", clean_desc).strip()

        # If title became empty or too short, fallback to brand + supplier title
        if len(clean_title) < 3:
            clean_title = source.supplier_title or "Product"

        # Final check: Title and description must exist
        passed = len(clean_title) >= 3 and len(clean_desc) >= 20

        if not passed:
            errors.append("Generated product copy failed factual verification and could not be sanitized.")

        return ValidationResult(
            passed=passed,
            title=clean_title,
            description=clean_desc,
            verified_claims=verified_claims,
            stripped_claims=stripped_claims,
            errors=errors,
        )
