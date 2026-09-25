import re
import hashlib

def build_store_context(business: dict, brand: dict) -> dict:
    ctx = {
        "brand_name": business.get("business_name", "Our Store"),
        "store_name": business.get("business_name", "Our Store"),
        "legal_business_name": business.get("business_name", "Our Store"),
        "domain": business.get("domain_name", "example.com"),
        
        "support_email": business.get("email", "support@example.com"),
        "phone": business.get("phone", ""),
        
        "business_address": business.get("address", ""),
        "business_city": business.get("city", ""),
        "business_state": business.get("state", ""),
        "business_zip": business.get("zip", ""),
        "business_country": business.get("country", ""),
        
        "niche": business.get("product_genre", "general"),
        "currency": business.get("currency", "USD"),
        
        "processing_time": business.get("processing_time", "1-2 business days"),
        "transit_time": business.get("transit_time", "3-5 business days"),
        "estimated_delivery_time": business.get("estimated_delivery_time", "4-7 business days"),
        "shipping_regions": business.get("shipping_regions", "the United States"),
        "shipping_cost": business.get("shipping_cost", "Free"),
        "free_shipping": business.get("free_shipping", "Yes"),
        
        "return_window": business.get("return_window", "30 days"),
        "return_method": business.get("return_method", "by mail"),
        "return_shipping_cost": business.get("return_shipping_cost", "customer responsibility"),
        "refund_processing_time": business.get("refund_processing_time", "5-7 business days"),
        
        "cancellation_window": business.get("cancellation_window", "12 hours"),
        
        "warranty_enabled": business.get("warranty_enabled", "No"),
        "warranty_period": business.get("warranty_period", "None"),
        
        "payment_methods": business.get("payment_methods", "Visa, Mastercard, American Express, Discover"),
        
        "support_hours": business.get("support_hours", "Mon-Fri 9AM-5PM"),
        "support_timezone": business.get("support_timezone", "EST"),
    }
    
    niche = str(ctx["niche"]).lower()
    if "lawn" in niche or "garden" in niche:
        ctx["niche_label"] = "Lawn & Garden Equipment"
        ctx["product_term"] = "lawn, garden and outdoor equipment"
        ctx["customer_need"] = "maintaining outdoor spaces"
        ctx["niche_description"] = "high-quality tools and machinery for your yard"
    elif "pet" in niche:
        ctx["niche_label"] = "Pet Supplies"
        ctx["product_term"] = "pet products and accessories"
        ctx["customer_need"] = "supporting pets and their owners"
        ctx["niche_description"] = "everything you need for a happy, healthy pet"
    elif "home" in niche or "furniture" in niche:
        ctx["niche_label"] = "Home & Furniture"
        ctx["product_term"] = "home furnishings and decor"
        ctx["customer_need"] = "creating a beautiful living space"
        ctx["niche_description"] = "stylish and comfortable additions to your home"
    elif "electronic" in niche:
        ctx["niche_label"] = "Electronics"
        ctx["product_term"] = "electronic devices and accessories"
        ctx["customer_need"] = "staying connected and productive"
        ctx["niche_description"] = "the latest technology for your daily life"
    else:
        ctx["niche_label"] = "General Ecommerce"
        ctx["product_term"] = "premium products"
        ctx["customer_need"] = "enhancing your lifestyle"
        ctx["niche_description"] = "carefully curated items for our customers"
        
    return ctx

def select_variant(domain: str, variants: list) -> int:
    if not variants:
        return 0
    hash_val = int(hashlib.md5(domain.encode('utf-8')).hexdigest(), 16)
    return hash_val % len(variants)

def render_template(template: str, ctx: dict) -> str:
    rendered = template
    for key, value in ctx.items():
        placeholder = f"{{{{{key}}}}}"
        if value:
            rendered = rendered.replace(placeholder, str(value))
        else:
            # If value is empty, remove the placeholder or keep it clean
            rendered = rendered.replace(placeholder, "")
    
    # Remove any stray placeholders that weren't in context
    rendered = re.sub(r'\{\{[a-zA-Z0-9_]+\}\}', '', rendered)
    return rendered
