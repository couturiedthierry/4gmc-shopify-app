from .context import build_store_context, select_variant, render_template
from . import templates

PAGE_KINDS = {
    'about_us': templates.ABOUT_US,
    'contact': templates.CONTACT_US,
    'faq': templates.FAQ,
    'legal_notice': templates.LEGAL_NOTICE,
    'privacy': templates.PRIVACY,
    'payment_policy': templates.PAYMENT,
    'shipping': templates.SHIPPING,
    'terms': templates.TERMS,
    'returns': templates.RETURNS,
    'cancellation_policy': templates.CANCELLATION,
    'warranty_policy': templates.WARRANTY,
    
    # Map old keys if necessary
    'contact_information': templates.CONTACT_US,
    'terms_of_sale': templates.TERMS,
}

def generate_static_page(kind: str, business: dict, brand: dict, force_variant: int = None) -> str:
    ctx = build_store_context(business, brand)
    
    variants = PAGE_KINDS.get(kind)
    if not variants:
        # Fallback to an empty page if unknown
        return f"<h1>{kind.replace('_', ' ').title()}</h1><p>Coming soon.</p>"
        
    if force_variant is not None and 0 <= force_variant < len(variants):
        variant_idx = force_variant
    else:
        variant_idx = select_variant(ctx['domain'], variants)
        
    template = variants[variant_idx]
    return render_template(template, ctx)
