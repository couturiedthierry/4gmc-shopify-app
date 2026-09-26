import os

def rewrite_app_js():
    with open('static/app.js', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines):
        if line.startswith(" return header('Pages & policies',"):
            # Replace lines 213 and 214 with the new UI
            new_code = (
                " return header('Pages & policies', 'Create complete Google Merchant Center-ready store information and policy pages from your store configuration.')+\n"
                "  `<div class=\"grid two-col\">\\n"
                "     <div class=\"grid\">\\n"
                "       <section class=\"card\">\\n"
                "         <h2>Static Brand Pages & Policies</h2>\\n"
                "         <p class=\"sub\">Generate required ecommerce pages deterministically with zero AI dependencies.</p>\\n"
                "         <ul style=\"list-style: none; padding: 0; margin-bottom: 24px;\">\\n"
                "           <li>✓ About Us</li>\\n"
                "           <li>✓ Contact Us</li>\\n"
                "           <li>✓ FAQ</li>\\n"
                "           <li>✓ Legal Notice</li>\\n"
                "           <li>✓ Privacy Policy</li>\\n"
                "           <li>✓ Payment Policy</li>\\n"
                "           <li>✓ Shipping Policy</li>\\n"
                "           <li>✓ Terms of Service</li>\\n"
                "           <li>✓ Refund & Return Policy</li>\\n"
                "           <li>✓ Order Cancellation Policy</li>\\n"
                "           <li>✓ Warranty Policy</li>\\n"
                "         </ul>\\n"
                "         <form id=\"policy-source-form\" class=\"form-grid\">\\n"
                "           <div class=\"full actions\">\\n"
                "             <button class=\"primary\" ${busy||generating?'disabled':''}>${generating?'Generating pages...':'GENERATE PAGES & POLICIES'}</button>\\n"
                "           </div>\\n"
                "         </form>\\n"
                "       </section>\\n"
                "       <section class=\"card\">\\n"
                "         <h2>Generated brand pages & policies</h2>\\n"
                "         <p class=\"sub\">${managed.length?`${managed.length} original documents generated for ${esc(data.store.business.business_name||data.store.name)}`:'Pages will appear here after generation.'}</p>\\n"
                "         ${result}${list}\\n"
                "         ${managed.length&&data.store.connected?'<div class=\"actions\" style=\"margin-top:16px\"><button class=\"secondary\" data-action=\"run-site-kit\">Publish verified brand pages</button></div>':''}\\n"
                "       </section>\\n"
                "     </div>\\n"
                "     <div class=\"grid\">\\n"
                "       <section class=\"card\">\\n"
                "         <h2>Destination identity</h2>\\n"
                "         <p class=\"sub\">Every generated page is built directly from these selected-store facts before Shopify publication.</p>\\n"
                "         ${check('Store name',Boolean(data.store.business.business_name),'Required throughout generated pages')}\\n"
                "         ${check('Product genre',Boolean(data.store.business.product_genre),esc(data.store.business.product_genre||'Tailors generated page tone and content'))}\\n"
                "         ${check('Domain',Boolean(data.store.business.domain_name),'Only your customer-facing domain is allowed')}\\n"
                "         ${check('Contact email',Boolean(data.store.business.email),'Required on contact and policies')}\\n"
                "         ${check('Store address',Boolean(data.store.business.address),'Used only where customer identity requires it')}\\n"
                "         ${check('Phone',Boolean(data.store.business.phone),'Required on the Contact page')}\\n"
                "         ${check('Country & currency',Boolean(data.store.business.country&&data.store.business.currency),'Used for destination policy context')}\\n"
                "         ${check('Shopify',data.store.connected,'Destination for automatic publication')}\\n"
                "         <div class=\"actions\"><button class=\"secondary\" data-view=\"business\">Edit store details</button></div>\\n"
                "       </section>\\n"
                "     </div>\\n"
                "   </div>`;\n"
            )
            lines[i] = new_code
            lines[i+1] = "\n"  # Clear the old line 214
            break
            
    with open('static/app.js', 'w', encoding='utf-8') as f:
        f.writelines(lines)
        
rewrite_app_js()
