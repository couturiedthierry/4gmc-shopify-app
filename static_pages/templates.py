from .multmarti import MULTMARTI_TEMPLATES

# We will provide 3 variants, but all 3 will use the MultMarti baseline 
# to ensure it strictly follows the MultMarti reference structure as requested by the user.

ABOUT_US = [
    MULTMARTI_TEMPLATES.get('about_us'),
    MULTMARTI_TEMPLATES.get('about_us'),
    MULTMARTI_TEMPLATES.get('about_us')
]

CONTACT_US = [
    MULTMARTI_TEMPLATES.get('contact'),
    MULTMARTI_TEMPLATES.get('contact'),
    MULTMARTI_TEMPLATES.get('contact')
]

FAQ = [
    MULTMARTI_TEMPLATES.get('faq'),
    MULTMARTI_TEMPLATES.get('faq'),
    MULTMARTI_TEMPLATES.get('faq')
]

LEGAL_NOTICE = [
    MULTMARTI_TEMPLATES.get('legal_notice'),
    MULTMARTI_TEMPLATES.get('legal_notice'),
    MULTMARTI_TEMPLATES.get('legal_notice')
]

PRIVACY = [
    MULTMARTI_TEMPLATES.get('privacy'),
    MULTMARTI_TEMPLATES.get('privacy'),
    MULTMARTI_TEMPLATES.get('privacy')
]

PAYMENT = [
    """<div><rte-formatter>
<p>At {{brand_name}}, we offer secure and flexible payment options to ensure a smooth checkout experience. All transactions are encrypted and processed through industry-leading payment gateways.</p>
<p><strong>Accepted Payment Methods</strong></p>
<p>We accept all major credit and debit cards, including Visa, Mastercard, American Express, and Discover. Depending on your region, accelerated checkout options such as Shop Pay, Apple Pay, and Google Pay may also be available at checkout.</p>
<p><strong>Payment Security</strong></p>
<p>Your security is our priority. {{brand_name}} does not store your full credit card information. Our payment processors are certified Level 1 PCI DSS compliant, ensuring that your payment details are protected with the highest level of encryption and fraud-prevention tools.</p>
<p><strong>Currency and Billing</strong></p>
<p>All prices are listed in your local currency where applicable. When you place an order, your payment method will be charged immediately. If you have any questions about billing or payment, please <a>contact us</a>.</p>
</rte-formatter></div>""",
    """<div><rte-formatter>
<p>At {{brand_name}}, we offer secure and flexible payment options to ensure a smooth checkout experience. All transactions are encrypted and processed through industry-leading payment gateways.</p>
<p><strong>Accepted Payment Methods</strong></p>
<p>We accept all major credit and debit cards, including Visa, Mastercard, American Express, and Discover. Depending on your region, accelerated checkout options such as Shop Pay, Apple Pay, and Google Pay may also be available at checkout.</p>
<p><strong>Payment Security</strong></p>
<p>Your security is our priority. {{brand_name}} does not store your full credit card information. Our payment processors are certified Level 1 PCI DSS compliant, ensuring that your payment details are protected with the highest level of encryption and fraud-prevention tools.</p>
<p><strong>Currency and Billing</strong></p>
<p>All prices are listed in your local currency where applicable. When you place an order, your payment method will be charged immediately. If you have any questions about billing or payment, please <a>contact us</a>.</p>
</rte-formatter></div>""",
    """<div><rte-formatter>
<p>At {{brand_name}}, we offer secure and flexible payment options to ensure a smooth checkout experience. All transactions are encrypted and processed through industry-leading payment gateways.</p>
<p><strong>Accepted Payment Methods</strong></p>
<p>We accept all major credit and debit cards, including Visa, Mastercard, American Express, and Discover. Depending on your region, accelerated checkout options such as Shop Pay, Apple Pay, and Google Pay may also be available at checkout.</p>
<p><strong>Payment Security</strong></p>
<p>Your security is our priority. {{brand_name}} does not store your full credit card information. Our payment processors are certified Level 1 PCI DSS compliant, ensuring that your payment details are protected with the highest level of encryption and fraud-prevention tools.</p>
<p><strong>Currency and Billing</strong></p>
<p>All prices are listed in your local currency where applicable. When you place an order, your payment method will be charged immediately. If you have any questions about billing or payment, please <a>contact us</a>.</p>
</rte-formatter></div>"""
]

SHIPPING = [
    MULTMARTI_TEMPLATES.get('shipping'),
    MULTMARTI_TEMPLATES.get('shipping'),
    MULTMARTI_TEMPLATES.get('shipping')
]

TERMS = [
    MULTMARTI_TEMPLATES.get('terms'),
    MULTMARTI_TEMPLATES.get('terms'),
    MULTMARTI_TEMPLATES.get('terms')
]

RETURNS = [
    MULTMARTI_TEMPLATES.get('returns'),
    MULTMARTI_TEMPLATES.get('returns'),
    MULTMARTI_TEMPLATES.get('returns')
]

CANCELLATION = [
    MULTMARTI_TEMPLATES.get('cancellation_policy'),
    MULTMARTI_TEMPLATES.get('cancellation_policy'),
    MULTMARTI_TEMPLATES.get('cancellation_policy')
]

WARRANTY = [
    MULTMARTI_TEMPLATES.get('warranty_policy'),
    MULTMARTI_TEMPLATES.get('warranty_policy'),
    MULTMARTI_TEMPLATES.get('warranty_policy')
]
