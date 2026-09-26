from .context import build_store_context, render_template
from .pdf_templates import PDF_TEMPLATES

TRACK_ORDER_TEMPLATE = """<h1>Track Your Order</h1>
<p>Once your order has been dispatched, you will receive an email containing a tracking number.</p>

<h2>How to Track</h2>
<p>Tracking information may take {{tracking_update_time}} to update after the carrier receives the shipment. Please enter your tracking number below to view the current status of your delivery.</p>

<p><em>[Tracking Component Integration - Connect this page to your store's tracking app or Shopify's native order status page]</em></p>

<h2>Need Help?</h2>
<p>If you cannot find your tracking number, or if there has been no update for several days, please contact our support team at <a href="mailto:{{contact_email}}">{{contact_email}}</a>. Make sure to include your order number so we can assist you quickly.</p>
"""

PAGE_KINDS = {
    'about_us': PDF_TEMPLATES.get('about_us'),
    'contact': PDF_TEMPLATES.get('contact_us'),
    'faq': PDF_TEMPLATES.get('faq'),
    'legal_notice': PDF_TEMPLATES.get('legal_notice'),
    'privacy': PDF_TEMPLATES.get('privacy_policy'),
    'payment_policy': PDF_TEMPLATES.get('payment_policy'),
    'shipping': PDF_TEMPLATES.get('shipping_policy'),
    'terms': PDF_TEMPLATES.get('terms_of_service'),
    'returns': PDF_TEMPLATES.get('refund_return_policy'),
    'cancellation_policy': PDF_TEMPLATES.get('order_cancellation_policy'),
    'warranty_policy': PDF_TEMPLATES.get('warranty_policy'),
    'track_order': TRACK_ORDER_TEMPLATE,
    
    # Map old keys if necessary
    'contact_information': PDF_TEMPLATES.get('contact_us'),
    'terms_of_sale': PDF_TEMPLATES.get('terms_of_service'),
}

def generate_static_page(kind: str, business: dict, brand: dict, ai_context: dict) -> str:
    ctx = build_store_context(business, brand, ai_context)
    
    template = PAGE_KINDS.get(kind)
    if not template:
        # Fallback to an empty page if unknown
        return f"<h1>{kind.replace('_', ' ').title()}</h1><p>Coming soon.</p>"
        
    return render_template(template, ctx)
