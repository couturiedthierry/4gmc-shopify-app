import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server

def test_policy_pages_structure_and_contextual_links():
    business = {
        'business_name': 'VYROX Industrial Co',
        'domain_name': 'vyrox.com',
        'email': 'support@vyrox.com',
        'phone': '+1 (800) 555-0199',
        'address': '100 Industrial Parkway, Austin, TX 78701',
        'country': 'United States',
        'currency': 'USD',
    }

    pages = server.standard_site_pages(business)

    # All 10 required policy & informational pages must exist
    required_kinds = {
        'about', 'contact', 'faq', 'shipping', 'returns', 'privacy',
        'terms', 'contact_information', 'legal_notice', 'terms_of_sale'
    }
    assert set(pages.keys()) == required_kinds, f"Missing pages in fallback set: {required_kinds - set(pages.keys())}"

    for kind, raw_body in pages.items():
        title = server.SITE_KIT_TITLES.get(kind, kind.replace('_', ' ').title())
        formatted_body = server.format_and_link_brand_page(title, raw_body, business)

        # 1. Must use semantic h2 or h3 headings
        assert re.search(r'<h[23]\b', formatted_body, re.I), f"Page '{kind}' missing semantic h2/h3 headings: {formatted_body}"

        # 2. Must use proper paragraphs <p> or list <ul>/<ol> elements
        assert re.search(r'<(p|ul|ol)\b', formatted_body, re.I), f"Page '{kind}' missing paragraphs or lists: {formatted_body}"

        # 3. Key labels must be bolded
        if any(label in formatted_body for label in ['Email:', 'Phone:', 'Shipping Cost:', 'Return Window:', 'Company Name:', 'Currency:']):
            assert '<strong>' in formatted_body, f"Page '{kind}' missing bold labels <strong>: {formatted_body}"

        # 4. Email must be mailto link if email is present
        if 'support@vyrox.com' in formatted_body:
            assert 'mailto:support@vyrox.com' in formatted_body, f"Page '{kind}' missing mailto link for support@vyrox.com"

        # 5. Phone must be tel link if phone is present
        if business['phone'] in formatted_body:
            assert 'tel:18005550199' in formatted_body, f"Page '{kind}' missing tel link for phone"

        # 6. Destination links test
        if kind in ('about', 'contact', 'faq', 'shipping', 'returns', 'terms', 'contact_information', 'legal_notice', 'terms_of_sale'):
            # Must contain contextual relative link to policies or pages
            assert re.search(r'href="/(?:policies|pages)/[a-z0-9-]+"', formatted_body), f"Page '{kind}' missing contextual relative link: {formatted_body}"

    print("ALL POLICY PAGES HTML STRUCTURE & CONTEXTUAL LINK VERIFICATIONS PASSED 100%!")

if __name__ == '__main__':
    test_policy_pages_structure_and_contextual_links()
