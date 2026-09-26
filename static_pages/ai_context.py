import json
import hashlib
import time

def build_context_hash(business: dict, brand: dict) -> str:
    """Hash the inputs that should trigger an AI context regeneration."""
    inputs = {
        'name': business.get('business_name', ''),
        'domain': business.get('domain_name', ''),
        'niche': business.get('product_genre', ''),
    }
    input_str = json.dumps(inputs, sort_keys=True)
    return hashlib.sha256(input_str.encode('utf-8')).hexdigest()

async def get_or_generate_store_context(c, store_id: int, business: dict, brand: dict, generate_func) -> dict:
    """
    Check if a valid AI context exists for the store. If not, call generate_func()
    to create it, and save it in the database.
    """
    current_hash = build_context_hash(business, brand)
    
    # Try to load existing context
    row = c.execute("SELECT content_context, content_hash FROM stores WHERE id=?", (store_id,)).fetchone()
    if row and row['content_context'] and row['content_hash'] == current_hash:
        try:
            return json.loads(row['content_context'])
        except json.JSONDecodeError:
            pass # Invalid JSON, regenerate
            
    # Need to generate
    niche = business.get('product_genre', 'premium products')
    brand_name = business.get('business_name', 'Our Store')
    
    prompt = f"""You are generating reusable ecommerce brand context for an online store.
Use ONLY the provided store information.
Do NOT invent business history, founding year, number of customers, certifications, awards, warehouses, employees, product specs, warranties, shipping times, return periods, guarantees, or payment methods unless explicitly provided.
Do NOT generate legal terms or compliance claims.
Do NOT output Markdown. Do NOT output HTML.
Return valid JSON matching the exact schema requested.

Store Information:
Brand Name: {brand_name}
Niche / Product Genre: {niche}

Generate a JSON object with this exact structure:
{{
  "brand_description": "1-2 sentences describing the brand and its focus.",
  "niche_description": "1-2 sentences describing the types of products sold.",
  "about": {{
    "intro": "1 sentence introductory statement about what the store offers.",
    "mission": "1 sentence mission statement.",
    "product_scope": "1 sentence describing the product range.",
    "customer_commitment": "1 sentence about customer service commitment."
  }},
  "contact": {{
    "intro": "1 sentence encouraging customers to reach out.",
    "support_description": "1 sentence about what support can assist with."
  }},
  "faq": {{
    "product_questions": [
      {{
        "question": "A niche-specific question (e.g. What types of [niche] do you offer?)",
        "answer": "Answer based only on the provided niche."
      }}
    ],
    "product_support_intro": "1 sentence about product-related questions."
  }},
  "warranty": {{
    "product_context": "1 sentence mentioning that eligible products in the [niche] category may be covered."
  }},
  "footer": {{
    "brand_description": "1 short sentence describing the brand for the footer."
  }},
  "homepage": {{
    "short_brand_description": "A very brief 3-5 word description of the brand."
  }}
}}
"""
    # Call the provided LLM function
    ai_data = await generate_func(prompt, max_tokens=1500)
    
    if not isinstance(ai_data, dict) or 'brand_description' not in ai_data:
        # Fallback if generation fails
        ai_data = {
            "brand_description": f"{brand_name} is an online store focused on {niche}.",
            "niche_description": f"The store offers equipment and items related to {niche}.",
            "about": {
                "intro": f"{brand_name} brings together {niche} for everyday needs.",
                "mission": "Our focus is to make useful equipment easier to discover and purchase online.",
                "product_scope": f"Our range includes various {niche}.",
                "customer_commitment": "We aim to provide clear product information, straightforward ordering and accessible customer support."
            },
            "contact": {
                "intro": f"Questions about {brand_name} products or an existing order can be directed to our customer support team.",
                "support_description": "Support can assist with general product, order, delivery and return questions."
            },
            "faq": {
                "product_questions": [],
                "product_support_intro": f"Product-related questions can be sent to the {brand_name} support team."
            },
            "warranty": {
                "product_context": f"Warranty requests may relate to eligible {niche} purchased through the store."
            },
            "footer": {
                "brand_description": f"Practical {niche} for everyday maintenance."
            },
            "homepage": {
                "short_brand_description": f"Quality {niche}."
            }
        }
        
    # Save to database
    c.execute("UPDATE stores SET content_context=?, content_hash=? WHERE id=?", 
              (json.dumps(ai_data), current_hash, store_id))
              
    return ai_data
