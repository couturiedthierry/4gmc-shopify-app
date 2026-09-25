import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server

def test_heading_citation_bold_pipeline():
    business = {
        'business_name': 'Aura Home Goods',
        'domain_name': 'aurahome.com',
        'email': 'support@aurahome.com',
        'phone': '+1 (800) 555-0144',
        'address': '742 Evergreen Terrace, Springfield, OR 97477',
        'country': 'United States',
        'currency': 'USD',
    }

    # 1. Verify Standard Policy Pages (all 10 pages)
    pages = server.standard_site_pages(business)
    mandatory_three = {'contact_information', 'legal_notice', 'terms_of_sale'}
    assert mandatory_three.issubset(pages.keys()), f"Missing mandatory policies: {mandatory_three - set(pages.keys())}"

    for kind, raw_body in pages.items():
        title = server.SITE_KIT_TITLES.get(kind, kind.replace('_', ' ').title())
        html = server.format_and_link_brand_page(title, raw_body, business)

        # Title duplicate check: Page body must NOT duplicate the page title or have H1 in body
        assert not re.search(r'<h1\b[^>]*>.*?</h1>', html, re.I), f"Page '{kind}' should not contain <h1> duplicate in body"
        # H2/H3 check
        assert re.search(r'<h[23]\b[^>]*>.*?</h[23]>', html, re.I), f"Page '{kind}' missing <h2> or <h3> headings"
        # Bold labels
        assert '<strong>' in html, f"Page '{kind}' missing bold labels"
        # No nested links
        assert not re.search(r'<a\b[^>]*>(?:(?!</a>).)*?<a\b', html, re.I | re.S), f"Page '{kind}' contains nested <a> anchors"
        # No links inside headings
        assert not re.search(r'<h[1-6]\b[^>]*>(?:(?!</h[1-6]>).)*?<a\b', html, re.I | re.S), f"Page '{kind}' contains <a> inside a heading tag"
        # Email & phone link check
        if business['email'] in raw_body or business['email'] in html:
            assert 'mailto:support@aurahome.com' in html
        if business['phone'] in raw_body or business['phone'] in html:
            assert 'tel:18005550144' in html

    # 2. Verify AI Markdown Conversion (headings, bold, lists, citations)
    ai_raw_markdown = """# Custom Brand Policy
At Aura Home Goods, our mission is to deliver satisfaction with our products.

## Shipping & Delivery Terms
* Processing Time: 1 to 2 business days
* Delivery Time: 3 to 5 business days
* Shipping Cost: Free standard shipping across the United States

## Returns and Order Tracking
You can track your order using Track Your Order or reach out to Customer Support.
Please review our Shipping Policy, Refund Policy, and Terms of Sale before ordering.
For assistance, email support@aurahome.com or call +1 (800) 555-0144.
"""
    formatted_ai = server.format_and_link_brand_page("Custom Brand Policy", ai_raw_markdown, business)

    # Must NOT contain duplicate H1 title, but must contain H2, UL, strong labels
    assert '<h1>Custom Brand Policy</h1>' not in formatted_ai
    assert '<h1' not in formatted_ai
    assert '<h2>Shipping &amp; Delivery Terms</h2>' in formatted_ai or '<h2>Shipping & Delivery Terms</h2>' in formatted_ai
    assert '<ul>' in formatted_ai
    assert '<strong>Processing Time:</strong>' in formatted_ai
    assert '<strong>Delivery Time:</strong>' in formatted_ai
    assert '<strong>Shipping Cost:</strong>' in formatted_ai

    # Paragraphs should NOT be stuck inside <h2> tags
    assert not re.search(r'<h2>(?:(?!</h2>).)*?<ul>', formatted_ai, re.I | re.S), "Lists were incorrectly wrapped inside <h2>"
    assert not re.search(r'<h2>(?:(?!</h2>).)*?<strong>Processing Time:</strong>', formatted_ai, re.I | re.S), "Content was trapped inside <h2>"

    # Contextual relative links
    assert '<a href="/pages/track-your-order">Track Your Order</a>' in formatted_ai
    assert '<a href="/policies/shipping-policy">Shipping Policy</a>' in formatted_ai
    assert '<a href="/policies/refund-policy">Refund Policy</a>' in formatted_ai
    assert '<a href="/policies/terms-of-sale">Terms of Sale</a>' in formatted_ai

    # 3. Verify Markdown bold syntax **bold**
    bold_md = """## Return Guidelines
**Return Window:** 30 days from delivery.
**Return Costs:** Free returns on defective items.
Ensure that **all original packaging** is preserved.
"""
    formatted_bold = server.format_and_link_brand_page("Return Guidelines", bold_md, business)
    assert '<strong>Return Window:</strong>' in formatted_bold
    assert '<strong>Return Costs:</strong>' in formatted_bold
    assert '<strong>all original packaging</strong>' in formatted_bold
    assert '**' not in formatted_bold, "Raw markdown asterisks remained in formatted HTML"

    # 4. Verify Headings with Attributes Do Not Trap Links
    attributed_md = """<h2 class="brand-section-header">Shipping Policy</h2>
<p>Refer to our Shipping Policy for full delivery conditions.</p>
"""
    formatted_attr = server.format_and_link_brand_page("Policy", attributed_md, business)
    assert '<h2 class="brand-section-header">Shipping Policy</h2>' in formatted_attr, "Heading text was corrupted with link"
    assert '<p>Refer to our <a href="/policies/shipping-policy">Shipping Policy</a>' in formatted_attr

    # 5. Verify Prevention of Duplicate Page Title Headings
    # Case A: Triple About Us matching user's live screenshot
    triple_about = """<h1>ABOUT US</h1>
<h2>ABOUT US</h2>
<p>Welcome to VYROX, your trusted destination for dependable lawn care.</p>
<h2>OUR MISSION</h2>
<p>Our mission is to provide reliable equipment.</p>
<h2>WHAT WE BELIEVE</h2>
<p>We believe in quality.</p>"""
    cleaned_about = server.format_and_link_brand_page("About Us", triple_about, {'business_name': 'VYROX'})
    assert '<h1' not in cleaned_about, "Body must not contain H1 title"
    assert '<h2>ABOUT US</h2>' not in cleaned_about, "Duplicate title H2 must be removed"
    assert '<h2>About Us</h2>' not in cleaned_about, "Duplicate title H2 must be removed"
    assert '<h2>OUR MISSION</h2>' in cleaned_about, "Subsequent section heading was preserved"
    assert '<h2>WHAT WE BELIEVE</h2>' in cleaned_about, "Subsequent section heading was preserved"

    # Case B: Markdown duplicate title headers # About Us and ## About Us
    md_about = """# About Us
## About Us
Welcome to VYROX.

## Our Mission
Our mission is clear."""
    cleaned_md = server.format_and_link_brand_page("About Us", md_about, {'business_name': 'VYROX'})
    assert '<h1' not in cleaned_md
    assert '<h2>About Us</h2>' not in cleaned_md
    assert '<h2>Our Mission</h2>' in cleaned_md
    assert '<p>Welcome to VYROX.</p>' in cleaned_md

    print("ALL HEADING, CITATION, AND BOLD PIPELINE TESTS PASSED 100%!")

if __name__ == '__main__':
    test_heading_citation_bold_pipeline()
