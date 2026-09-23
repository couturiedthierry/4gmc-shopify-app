"""Product Source Record & Verified Technical Fact Extractor for 4GMC.

Extracts verified technical attributes with source evidence and confidence scores
from supplier product data. Any technical claim lacking evidence is classified as UNKNOWN.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Strict whitelist of technical attributes that MUST be verified from source evidence
TECHNICAL_ATTRIBUTE_KEYS = {
    "voltage",
    "wattage",
    "amperage",
    "battery_capacity",
    "engine_displacement",
    "cutting_width",
    "pressure",
    "rpm",
    "dimensions",
    "weight",
    "material",
    "runtime",
    "motor_type",
    "filtration_claims",
    "warranty",
    "compatibility",
    "certifications",
}

# Patterns to locate evidence in text
ATTRIBUTE_PATTERNS: dict[str, list[str]] = {
    "voltage": [r"(\d+(?:\.\d+)?\s*V(?:olts?)?)", r"(\d+(?:\.\d+)?v)"],
    "wattage": [r"(\d+(?:\.\d+)?\s*W(?:atts?)?)", r"(\d+(?:\.\d+)?w)"],
    "amperage": [r"(\d+(?:\.\d+)?\s*A(?:mps?)?)"],
    "battery_capacity": [r"(\d+(?:\.\d+)?\s*Ah)", r"(\d+(?:\.\d+)?\s*mAh)"],
    "engine_displacement": [r"(\d+(?:\.\d+)?\s*cc)", r"(\d+(?:\.\d+)?\s*ccm)"],
    "cutting_width": [r"(\d+(?:\.\d+)?\s*(?:inch|in|cm|mm)\s*(?:cutting\s*width|deck))"],
    "pressure": [r"(\d+(?:\.\d+)?\s*PSI)", r"(\d+(?:\.\d+)?\s*bar)"],
    "rpm": [r"(\d+(?:\,\d+)?\s*RPM)"],
    "dimensions": [r"(\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?\s*(?:in|cm|mm)?)"],
    "weight": [r"(\d+(?:\.\d+)?\s*(?:lbs?|kg|oz))"],
    "material": [r"(stainless steel|aluminum|cast iron|abs plastic|polycarbonate|carbon steel)"],
    "runtime": [r"(\d+\s*(?:mins?|minutes?|hours?|hrs?)\s*(?:run\s*time|runtime|battery\s*life))"],
    "motor_type": [r"(brushless\s*motor|brushed\s*motor|induction\s*motor)"],
    "filtration_claims": [r"(hepa(?:\s*filter)?|true\s*hepa|washable\s*filter|cyclonic\s*filtration)"],
    "warranty": [r"(\d+\s*year\s*warranty|\d+\s*yr\s*warranty|lifetime\s*warranty)"],
    "compatibility": [r"(compatible\s*with\s*[^.,;]+)"],
    "certifications": [r"(ul\s*listed|ce\s*certified|etl\s*listed|fcc\s*approved|energy\s*star)"],
}


@dataclass
class VerifiedAttribute:
    value: str
    source: str = "supplier"
    confidence: float = 1.0
    evidence_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "source": self.source,
            "confidence": self.confidence,
            "evidence_text": self.evidence_text,
        }


@dataclass
class ProductSource:
    product_id: str
    supplier_title: str
    supplier_description: str
    supplier_images: list[str] = field(default_factory=list)
    supplier_url: str = ""
    sku: str = ""
    mpn: str = ""
    gtin: str = ""
    verified_attributes: dict[str, VerifiedAttribute] = field(default_factory=dict)
    unknown_attributes: list[str] = field(default_factory=list)
    source_evidence: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "supplier_title": self.supplier_title,
            "supplier_description": self.supplier_description,
            "supplier_images": self.supplier_images,
            "supplier_url": self.supplier_url,
            "sku": self.sku,
            "mpn": self.mpn,
            "gtin": self.gtin,
            "verified_attributes": {k: v.to_dict() for k, v in self.verified_attributes.items()},
            "unknown_attributes": self.unknown_attributes,
            "source_evidence": self.source_evidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProductSource:
        raw_attrs = data.get("verified_attributes", {})
        verified = {
            k: VerifiedAttribute(**v) if isinstance(v, dict) else v
            for k, v in raw_attrs.items()
        }
        return cls(
            product_id=str(data.get("product_id", "")),
            supplier_title=str(data.get("supplier_title", "")),
            supplier_description=str(data.get("supplier_description", "")),
            supplier_images=list(data.get("supplier_images", [])),
            supplier_url=str(data.get("supplier_url", "")),
            sku=str(data.get("sku", "")),
            mpn=str(data.get("mpn", "")),
            gtin=str(data.get("gtin", "")),
            verified_attributes=verified,
            unknown_attributes=list(data.get("unknown_attributes", [])),
            source_evidence=dict(data.get("source_evidence", {})),
        )


class ProductSourceExtractor:
    """Extracts truthful ProductSource record from imported supplier data."""

    @staticmethod
    def extract(
        product_id: str,
        supplier_data: dict[str, Any],
        supplier_url: str = "",
        sku: str = "",
        mpn: str = "",
        gtin: str = "",
    ) -> ProductSource:
        title = str(supplier_data.get("title", "")).strip()
        desc = str(supplier_data.get("description") or supplier_data.get("body_html") or "").strip()
        images = []
        for img in supplier_data.get("images", []):
            if isinstance(img, str):
                images.append(img)
            elif isinstance(img, dict) and img.get("src"):
                images.append(str(img["src"]))

        full_text = f"{title}\n{desc}"
        verified: dict[str, VerifiedAttribute] = {}
        evidence: dict[str, str] = {}
        unknown: list[str] = []

        for key in TECHNICAL_ATTRIBUTE_KEYS:
            patterns = ATTRIBUTE_PATTERNS.get(key, [])
            matched_value = None
            evidence_snippet = None

            for pat in patterns:
                match = re.search(pat, full_text, re.IGNORECASE)
                if match:
                    matched_value = match.group(1).strip()
                    start = max(0, match.start() - 30)
                    end = min(len(full_text), match.end() + 30)
                    evidence_snippet = full_text[start:end].strip()
                    break

            if matched_value:
                verified[key] = VerifiedAttribute(
                    value=matched_value,
                    source="supplier",
                    confidence=1.0,
                    evidence_text=evidence_snippet or matched_value,
                )
                evidence[key] = evidence_snippet or matched_value
            else:
                unknown.append(key)

        return ProductSource(
            product_id=product_id,
            supplier_title=title,
            supplier_description=desc,
            supplier_images=images,
            supplier_url=supplier_url,
            sku=sku,
            mpn=mpn,
            gtin=gtin,
            verified_attributes=verified,
            unknown_attributes=unknown,
            source_evidence=evidence,
        )
