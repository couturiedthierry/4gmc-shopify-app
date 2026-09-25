import asyncio
import unittest
import json
import hashlib
from unittest.mock import patch, MagicMock

import server
from static_pages.context import build_store_context, select_variant
from static_pages.generator import PAGE_KINDS, generate_static_page
from fastapi.testclient import TestClient

client = TestClient(server.app)

def test_three_variants_exist():
    # Verify exactly three complete templates are available for each supported document
    assert len(PAGE_KINDS) >= 11
    for kind, variants in PAGE_KINDS.items():
        assert len(variants) == 3, f"Expected 3 variants for {kind}, got {len(variants)}"
        for variant in variants:
            assert len(variant.strip()) > 100, f"Variant for {kind} seems too short or empty"

def test_stable_selection():
    # Same brand/domain always selects same automatic variant
    v1 = select_variant('example.com', [1, 2, 3])
    v2 = select_variant('example.com', [1, 2, 3])
    assert v1 == v2
    
    v3 = select_variant('another.com', [1, 2, 3])
    # Very likely different or same, but deterministic
    assert select_variant('another.com', [1, 2, 3]) == v3

def test_no_multmarti_leakage():
    # Search all output for MultMarti or multmarti.com
    for kind, variants in PAGE_KINDS.items():
        for variant in variants:
            assert "MultMarti" not in variant, f"MultMarti found in {kind}"
            assert "multmarti.com" not in variant, f"multmarti.com found in {kind}"
            assert "VYROX" not in variant
            assert "ZYPLAN" not in variant

def test_missing_optional_data():
    business = {
        "business_name": "Test Brand",
        "domain_name": "test.com",
    }
    ctx = build_store_context(business, {})
    assert ctx["phone"] == ""
    assert ctx["warranty_enabled"] == "No"
    
    # Output should still be clean
    body = generate_static_page('warranty_policy', business, {})
    assert "Test Brand" in body
    assert "No" in body

def test_brand_replacement():
    b1 = {"business_name": "Brand A", "domain_name": "a.com"}
    b2 = {"business_name": "Brand B", "domain_name": "b.com"}
    
    out1 = generate_static_page('about_us', b1, {}, force_variant=0)
    out2 = generate_static_page('about_us', b2, {}, force_variant=0)
    
    assert "Brand A" in out1
    assert "Brand B" not in out1
    assert "Brand B" in out2
    assert "Brand A" not in out2

def test_policy_consistency():
    business = {
        "business_name": "Consistent Co",
        "return_window": "99 days",
        "shipping_cost": "$5 flat"
    }
    out_returns = generate_static_page('returns', business, {}, force_variant=0)
    out_faq = generate_static_page('faq', business, {}, force_variant=0)
    out_shipping = generate_static_page('shipping', business, {}, force_variant=0)
    
    assert "99 days" in out_returns
    assert "99 days" in out_faq
    assert "$5 flat" in out_shipping
    assert "$5 flat" in out_faq

@patch('server.ai_json')
@patch('site_kit.collect_policies')
@patch('site_kit.collect_pages')
def test_no_ai_and_no_network_reference(mock_collect_pages, mock_collect_policies, mock_ai_json):
    mock_ai_json.side_effect = Exception("AI call attempted!")
    mock_collect_policies.side_effect = Exception("Scraping attempted!")
    mock_collect_pages.side_effect = Exception("Scraping attempted!")
    
    # Pre-configure the DB with a store
    with server.db() as c:
        business = {
            "business_name": "Test Store",
            "domain_name": "test.com",
            "email": "test@test.com",
            "address": "123 Test St",
            "phone": "555-5555",
            "country": "US",
            "currency": "USD"
        }
        c.execute('UPDATE stores SET business=? WHERE id=1', (json.dumps(business),))
        
    with patch('server.require', return_value=None):
        response = client.post('/api/site-kit/prepare', json={'source_url': ''})
    assert response.status_code == 200, response.text
    
    plan = response.json()
    assert len(plan['pages']) >= 11
    
    # Internal links
    for page in plan['pages']:
        assert "multmarti.com" not in page['body']
        
    # Verify mock was not called
    mock_ai_json.assert_not_called()
    mock_collect_policies.assert_not_called()
    mock_collect_pages.assert_not_called()

class TestSiteKitStatic(unittest.TestCase):
    def test_three_variants_exist(self): test_three_variants_exist()
    def test_stable_selection(self): test_stable_selection()
    def test_no_multmarti_leakage(self): test_no_multmarti_leakage()
    def test_missing_optional_data(self): test_missing_optional_data()
    def test_brand_replacement(self): test_brand_replacement()
    def test_policy_consistency(self): test_policy_consistency()
    
    @patch('server.ai_json')
    @patch('site_kit.collect_policies')
    @patch('site_kit.collect_pages')
    def test_no_ai_and_no_network_reference(self, mock_collect_pages, mock_collect_policies, mock_ai_json):
        test_no_ai_and_no_network_reference.__wrapped__(mock_collect_pages, mock_collect_policies, mock_ai_json)

if __name__ == '__main__':
    unittest.main()
