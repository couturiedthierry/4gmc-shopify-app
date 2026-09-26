import re
import hashlib
import datetime

def build_store_context(business: dict, brand: dict, ai_context: dict) -> dict:
    ctx = {
        # Business/Brand Fact Variables
        "store_name": business.get("business_name", "Our Store"),
        "domain_name": business.get("domain_name", "example.com"),
        "contact_email": business.get("email", "support@example.com"),
        "primary_color": brand.get("color", "#2251dc"),
        "store_address": business.get("address", ""),
        "target_country": business.get("country", "United States"),
        "currency": business.get("currency", "USD"),
        "phone": business.get("phone", ""),
        "product_niche": business.get("product_genre", "general merchandise"),
        "product_term": business.get("product_genre", "general merchandise"), # Deterministic short term
        "support_hours": business.get("support_hours", "Mon-Fri: 9:00 AM - 5:00 PM"),
        "support_timezone": business.get("support_timezone", "EST"),
        
        "shipping_destination": business.get("shipping_regions", "the United States"),
        "shipping_cost_text": "Free Standard Shipping on all orders" if str(business.get("free_shipping", "")).lower() in ["yes", "true", "1"] else "Shipping costs are calculated at checkout",
        "shipping_cutoff": "5:00 PM",
        "handling_time": business.get("processing_time", "1-2 business days"),
        "transit_time": business.get("transit_time", "3-5 business days"),
        "estimated_delivery_time": business.get("estimated_delivery_time", "4-7 business days"),
        "tracking_update_time": "24-48 hours",
        
        "return_window_days": str(business.get("return_window", "30")).replace(" days", ""),
        "return_method": business.get("return_method", "by mail"),
        "return_fee_text": "Customer is responsible for return shipping costs" if str(business.get("return_shipping_cost", "")).lower() == "customer responsibility" else "We provide a free prepaid return label",
        "restocking_fee_text": "No restocking fee",
        "refund_processing_time": business.get("refund_processing_time", "5-7 business days"),
        
        "cancellation_window_hours": str(business.get("cancellation_window", "12")).replace(" hours", ""),
        
        "warranty_enabled": business.get("warranty_enabled", "No"),
        "warranty_period": business.get("warranty_period", "1 year"),
        "payment_methods": business.get("payment_methods", "Visa, Mastercard, American Express, Discover"),
        "payment_processor": "Shopify Payments",
        
        "legal_business_name": business.get("business_name", "Our Store"),
        "legal_representative": "",
        "governing_region": business.get("state", "") or "our operating jurisdiction",
        "current_year": str(datetime.datetime.now().year),
        
        # Niche rules
        "niche_shipping_clause": "We do not ship gas or fuel. Products are shipped dry.",
        "niche_return_restrictions": "Products must be unused, uninstalled, and free of any gas or fluids.",
        "non_returnable_items": "Gift cards, downloadable software products, and hazardous materials",
        "non_cancellable_items": "Gift cards and custom products",
        "exchange_policy_text": "We do not offer direct exchanges. Please return your item for a refund and place a new order.",
        "warranty_shipping_cost_text": "We cover shipping in both directions for an approved warranty claim",
        "warranty_transferability_text": "This warranty is extended to the original purchaser only and is not transferable",
        
        # Additional fields
        "warranty_faq_answer": "Eligible products are covered for 1 year under the Warranty Policy." if str(business.get("warranty_enabled", "")).lower() == "yes" else "Warranty terms are product-specific; refer to the product page.",
        "warranty_intro": "This policy describes the limited warranty offered by our store for eligible products." if str(business.get("warranty_enabled", "")).lower() == "yes" else "Warranty terms are product-specific; refer to the product page.",
        "warranty_exclusions": "Wear parts and consumables, normal wear and tear, and damage from misuse",
    }
    
    niche = str(ctx["product_niche"]).lower()
    if "lawn" in niche or "garden" in niche:
        ctx["product_term"] = "outdoor and garden equipment"
    elif "pet" in niche:
        ctx["product_term"] = "pet products and accessories"
        ctx["niche_shipping_clause"] = "No special shipping restrictions apply to standard pet supplies."
        ctx["niche_return_restrictions"] = "For hygiene reasons, pet beds and toys must be completely unused."
    elif "electronic" in niche:
        ctx["product_term"] = "consumer electronics"
        ctx["niche_shipping_clause"] = "Lithium batteries are shipped according to carrier safety regulations."
        ctx["niche_return_restrictions"] = "Electronics must be returned in original packaging with all accessories."
    elif "apparel" in niche or "clothing" in niche:
        ctx["product_term"] = "clothing and accessories"
        ctx["niche_shipping_clause"] = "No special shipping restrictions apply."
        ctx["niche_return_restrictions"] = "Clothing must be unworn, unwashed, and with all original tags attached."
        
    # Merge AI context
    if ai_context:
        ctx["brand_description"] = ai_context.get("brand_description", "")
        ctx["niche_description"] = ai_context.get("niche_description", "")
        about = ai_context.get("about", {})
        ctx["about.intro"] = about.get("intro", "")
        ctx["about.mission"] = about.get("mission", "")
        ctx["about.product_scope"] = about.get("product_scope", "")
        ctx["about.customer_commitment"] = about.get("customer_commitment", "")
        
        contact = ai_context.get("contact", {})
        ctx["contact.intro"] = contact.get("intro", "")
        ctx["contact.support_description"] = contact.get("support_description", "")
        
        faq = ai_context.get("faq", {})
        ctx["faq.product_support_intro"] = faq.get("product_support_intro", "")
        
        # Format the AI-generated niche questions into HTML paragraphs
        faq_questions_html = ""
        questions = faq.get("product_questions", [])
        if questions and isinstance(questions, list):
            for q in questions:
                question = q.get("question", "")
                answer = q.get("answer", "")
                if question and answer:
                    faq_questions_html += f"<p><strong>{question}</strong><br>\\n{answer}</p>\\n\\n"
        
        ctx["faq.product_questions_html"] = faq_questions_html
        
        warranty = ai_context.get("warranty", {})
        ctx["warranty.product_context"] = warranty.get("product_context", "")
        
    return ctx

def render_template(template: str, ctx: dict) -> str:
    # First, handle conditional blocks like [[IF warranty_enabled]] ... [[ELSE]] ...
    def replace_conditional(match):
        condition_var = match.group(1).strip()
        true_text = match.group(2)
        false_text = match.group(3) if match.group(3) is not None else ""
        
        # Check condition
        val = str(ctx.get(condition_var, "")).lower()
        is_true = val in ["yes", "true", "1", "enabled"]
        
        return true_text if is_true else false_text

    # Matches [[IF var]] true_text [[ELSE]] false_text (ELSE is optional)
    # The regex needs to handle multiline.
    pattern = r'\[\[IF\s+([a-zA-Z0-9_]+)\]\](.*?(?:\[\[ELSE\]\](.*?))?)'
    # Wait, simple split might be safer, but let's try a regex for simple cases.
    
    # Actually, the PDF only uses [[IF warranty_enabled]] ... [[ELSE]] ...
    # Let's just do simple string replacements for the known ones.
    if "[[IF warranty_enabled]]" in template:
        if str(ctx.get("warranty_enabled", "")).lower() in ["yes", "true", "1"]:
            template = re.sub(r'\[\[IF warranty_enabled\]\](.*?)\[\[ELSE\]\](.*?)', r'\1', template, flags=re.DOTALL)
        else:
            template = re.sub(r'\[\[IF warranty_enabled\]\](.*?)\[\[ELSE\]\](.*?)', r'\2', template, flags=re.DOTALL)
            
    if "[[IF exchanges_enabled]]" in template:
        # Assuming no exchanges enabled unless specified
        template = re.sub(r'\[\[IF exchanges_enabled\]\](.*?)\[\[ELSE\]\](.*?)', r'\2', template, flags=re.DOTALL)
        
    if "[[IF niche_safety_clause]]" in template:
        if ctx.get("niche_safety_clause"):
            template = re.sub(r'\[\[IF niche_safety_clause\]\](.*?)\[\[ELSE\]\](.*?)', r'\1', template, flags=re.DOTALL)
        else:
            template = re.sub(r'\[\[IF niche_safety_clause\]\](.*?)\[\[ELSE\]\](.*?)', r'\2', template, flags=re.DOTALL)

    rendered = template
    for key, value in ctx.items():
        placeholder = f"{{{{{key}}}}}"
        if value:
            rendered = rendered.replace(placeholder, str(value))
        else:
            rendered = rendered.replace(placeholder, "")
    
    # Remove any stray placeholders
    rendered = re.sub(r'\{\{[a-zA-Z0-9_.]+\}\}', '', rendered)
    return rendered
