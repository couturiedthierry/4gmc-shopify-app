PDF_TEMPLATES = {
    "about_us": """<p>At {{store_name}}, we focus on {{product_term}} for customers who value clear information, practical selection and dependable service. Our catalog is shaped around the niche described by the store owner: {{product_niche}}.</p>

<h2>Our Mission</h2>
<p>Our mission is to make it easier to discover and purchase suitable {{product_term}} online. We aim to present products clearly, keep store policies easy to understand, and provide responsive support before and after an order.</p>

<h2>What We Believe</h2>
<p>We believe an online store should be straightforward: accurate product information, transparent pricing, realistic delivery expectations and policies that customers can find before checkout. We use those principles throughout {{store_name}}.</p>

<h2>Our Commitment</h2>
<p>{{store_name}} is committed to maintaining current product details, consistent policy information and customer support through <a href="mailto:{{contact_email}}">{{contact_email}}</a>. Where product-specific instructions, safety information or maintenance guidance apply, customers should follow the documentation supplied with the product.</p>

<h2>Why Shop With Us</h2>
<ul>
  <li><strong>Shipping:</strong> {{shipping_cost_text}}. Full details are available in the Shipping Policy.</li>
  <li><strong>Returns:</strong> Eligible return requests may be submitted within {{return_window_days}} days, subject to the Refund & Return Policy.</li>
  <li><strong>Checkout:</strong> Available payment methods are shown at checkout and described in the Payment Policy.</li>
  <li><strong>Support:</strong> {{support_hours}} ({{support_timezone}}), with contact available at <a href="mailto:{{contact_email}}">{{contact_email}}</a> and <a href="tel:{{phone}}">{{phone}}</a>.</li>
</ul>

<h2>Get In Touch</h2>
<p>Questions about a product, order or policy can be sent to <a href="mailto:{{contact_email}}">{{contact_email}}</a>. You may also contact us by phone at <a href="tel:{{phone}}">{{phone}}</a> or use the Contact Us page.</p>

<p><strong>Related Policies</strong><br>
<a href="/policies/shipping-policy">Shipping Policy</a> - <a href="/policies/refund-policy">Refund & Return Policy</a> - <a href="/pages/order-cancellation-policy">Order Cancellation Policy</a> - <a href="/policies/terms-of-service">Terms of Service</a> - <a href="/pages/contact-us">Contact Us</a></p>
""",
    "contact_us": """
<div style="display: flex; flex-wrap: wrap; gap: 40px; justify-content: space-between; max-width: 1200px; margin: 0 auto; line-height: 1.6;">
  
  <div style="flex: 1; min-width: 300px;">
    <h2 style="margin-top: 0;">Contact Us</h2>
    <p style="margin-bottom: 24px;">Have a question or need assistance with your order? We're here to help!</p>
    
    <h3 style="margin-bottom: 12px;">Contact Information</h3>
    <ul style="list-style: none; padding: 0; margin-bottom: 24px;">
      <li style="margin-bottom: 8px;"><strong>Store Name:</strong> {{store_name}}</li>
      <li style="margin-bottom: 8px;"><strong>Email:</strong> <a href="mailto:{{contact_email}}">{{contact_email}}</a></li>
      <li style="margin-bottom: 8px;"><strong>Phone:</strong> <a href="tel:{{phone}}">{{phone}}</a></li>
      <li style="margin-bottom: 8px;"><strong>Address:</strong> {{store_address}}</li>
    </ul>

    <h3 style="margin-bottom: 12px;">Customer Support Hours</h3>
    <ul style="list-style: none; padding: 0; margin-bottom: 24px;">
      <li style="margin-bottom: 8px;">Monday - Friday: {{support_hours}} ({{support_timezone}})</li>
      <li style="margin-bottom: 8px;">Saturday - Sunday: Closed (We'll respond on Monday)</li>
    </ul>

    <h3 style="margin-bottom: 12px;">Before You Write</h3>
    <p style="margin-bottom: 16px;">Many questions are answered on our FAQ page. You may also find what you need in one of the following:</p>
    <ul style="list-style: none; padding: 0;">
      <li style="margin-bottom: 12px;">Cancelling an order? See our <a href="/pages/order-cancellation-policy">Order Cancellation Policy</a> — requests must be made within {{cancellation_window_hours}} hours.</li>
      <li style="margin-bottom: 12px;">Returning an item? See our <a href="/policies/refund-policy">Refund & Return Policy</a> — {{return_window_days}} days from delivery.</li>
      <li style="margin-bottom: 12px;">Reporting a fault? See our <a href="/pages/warranty-policy">Warranty Policy</a> — one-year limited warranty, repair or replace.</li>
      <li style="margin-bottom: 12px;">Tracking a delivery? See our <a href="/pages/track-order">Tracking Order page</a></li>
    </ul>
  </div>

  <div style="flex: 1; min-width: 300px; background-color: #f9f9f9; padding: 32px; border-radius: 8px; align-self: flex-start;">
    <h2 style="margin-top: 0; margin-bottom: 24px;">Send Us a Message</h2>
    <form method="post" action="/contact#contact_form" accept-charset="UTF-8" class="contact-form">
      <input type="hidden" name="form_type" value="contact">
      <input type="hidden" name="utf8" value="✓">
      
      <div style="margin-bottom: 16px;">
        <label for="ContactFormName" style="display: block; margin-bottom: 8px; font-weight: bold; font-size: 14px;">Name</label>
        <input type="text" id="ContactFormName" name="contact[name]" style="width: 100%; padding: 12px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;" required>
      </div>
      
      <div style="margin-bottom: 16px;">
        <label for="ContactFormEmail" style="display: block; margin-bottom: 8px; font-weight: bold; font-size: 14px;">Email</label>
        <input type="email" id="ContactFormEmail" name="contact[email]" style="width: 100%; padding: 12px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;" required>
      </div>
      
      <div style="margin-bottom: 16px;">
        <label for="ContactFormPhone" style="display: block; margin-bottom: 8px; font-weight: bold; font-size: 14px;">Phone (optional)</label>
        <input type="tel" id="ContactFormPhone" name="contact[phone]" style="width: 100%; padding: 12px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;">
      </div>
      
      <div style="margin-bottom: 16px;">
        <label for="ContactFormOrder" style="display: block; margin-bottom: 8px; font-weight: bold; font-size: 14px;">Order Number (optional)</label>
        <input type="text" id="ContactFormOrder" name="contact[order_number]" style="width: 100%; padding: 12px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;">
      </div>
      
      <div style="margin-bottom: 24px;">
        <label for="ContactFormMessage" style="display: block; margin-bottom: 8px; font-weight: bold; font-size: 14px;">Message</label>
        <textarea rows="6" id="ContactFormMessage" name="contact[body]" style="width: 100%; padding: 12px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; resize: vertical;" required></textarea>
      </div>
      
      <button type="submit" style="width: 100%; padding: 14px; background-color: {{primary_color}}; color: #ffffff; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; text-transform: uppercase; font-size: 14px;">Send Message</button>
    </form>
  </div>
</div>
""",
    "faq": """
<h2>1. Shipping & Delivery</h2>

<h3>How long will it take to receive my order?</h3>
<p>Orders are normally prepared within {{handling_time}}. After dispatch, estimated transit time is {{transit_time}}, giving an overall estimate of {{estimated_delivery_time}}. Delivery dates are estimates and may be affected by carrier conditions.</p>

<h3>How much does shipping cost?</h3>
<p>{{shipping_cost_text}}.</p>

<h3>Where do you ship?</h3>
<p>Current shipping destination: {{shipping_destination}}.</p>

<h3>Are there niche-specific shipping restrictions?</h3>
<p>{{niche_shipping_clause}}</p>

<h2>2. Orders & Tracking</h2>

<h3>How can I track my order?</h3>
<p>When tracking is available, the customer receives shipment confirmation and a tracking reference. Tracking may take {{tracking_update_time}} to become active after dispatch.</p>

<h3>Can I change or cancel my order?</h3>
<p>Requests should be sent as soon as possible. If the configured cancellation window is {{cancellation_window_hours}} hours, the request must arrive within that period and before processing makes the change impossible. See <a href="/pages/order-cancellation-policy">Order Cancellation Policy</a>.</p>

<h2>3. Returns & Refunds</h2>

<h3>What is your return policy?</h3>
<p>Eligible items may be requested for return within {{return_window_days}} days of the applicable start date defined in the Refund & Return Policy. Returned items must meet the policy's condition and authorization requirements.</p>

<h3>How do I start a return?</h3>
<p>Contact <a href="mailto:{{contact_email}}">{{contact_email}}</a> with the order number and reason for return.</p>

<h3>Who pays for return shipping?</h3>
<p>{{return_fee_text}}.</p>

<h3>When will I receive my refund?</h3>
<p>Approved refunds are sent to the original payment method within {{refund_processing_time}}, after any required inspection. The customer's bank may need additional time to post the transaction.</p>

<h2>4. Warranty & Product Support</h2>

<h3>Is my product covered by a warranty?</h3>
<p>{{warranty_faq_answer}}</p>

<h3>How do I make a warranty claim?</h3>
<p>Contact <a href="mailto:{{contact_email}}">{{contact_email}}</a> with the order number, product identification, description of the issue and supporting photos/video where useful. Do not return the product until instructions are provided.</p>

<h2>5. Products & Choosing the Right {{product_term}}</h2>

<h3>How do I choose the right product?</h3>
<p>Use the specifications, intended-use information and compatibility details shown on each product page.</p>

<h3>Are product images accurate?</h3>
<p>Product images are intended to represent the item accurately, but screen settings and normal manufacturing variation can affect color or finish. Product specifications take precedence where appearance and specification differ.</p>

<h2>6. Payments & Security</h2>

<h3>What payment methods do you accept?</h3>
<p>{{payment_methods}}.</p>

<h3>When am I charged?</h3>


<h2>7. Support Hours</h2>
<p>{{support_hours}} ({{support_timezone}}). Email: <a href="mailto:{{contact_email}}">{{contact_email}}</a>. Phone: <a href="tel:{{phone}}">{{phone}}</a>. Address: {{store_address}}.</p>

<p><strong>Related Pages</strong><br>
<a href="/policies/shipping-policy">Shipping Policy</a> - <a href="/policies/refund-policy">Refund & Return Policy</a> - <a href="/pages/order-cancellation-policy">Order Cancellation Policy</a> - <a href="/pages/warranty-policy">Warranty Policy</a> - <a href="/policies/payment-policy">Payment Policy</a> - <a href="/pages/track-order">Track Order</a> - <a href="/pages/contact-us">Contact Us</a></p>
""",
    "legal_notice": """<p>This website is operated for the {{store_name}} online store. The information below identifies the business contact details and explains key rules governing use of the site.</p>

<h2>1. Business Information</h2>
<ul>
  <li><strong>Store Name:</strong> {{store_name}}</li>
  <li><strong>Legal Business Name:</strong> {{legal_business_name}}</li>
  <li><strong>Business Address:</strong> {{store_address}}</li>
  <li><strong>Legal Representative:</strong> {{legal_representative}}</li>
  <li><strong>Email:</strong> <a href="mailto:{{contact_email}}">{{contact_email}}</a></li>
  <li><strong>Phone:</strong> <a href="tel:{{phone}}">{{phone}}</a></li>
  <li><strong>Domain:</strong> {{domain_name}}</li>
</ul>

<h2>2. Intellectual Property</h2>
<p>Unless otherwise stated, the store's original branding, layout, written material and owned media are protected by applicable intellectual-property laws. Third-party trademarks and materials remain the property of their respective owners. Customers may use the website for normal personal shopping purposes and may not republish protected material without permission.</p>

<h2>3. Limitation of Liability</h2>
<p>The website is provided for ecommerce and informational purposes. To the extent permitted by law, {{store_name}} does not guarantee uninterrupted access or that every non-contractual website statement will always be error-free. Nothing in this section limits rights that cannot legally be excluded.</p>

<h2>4. Dispute Resolution</h2>
<p>Customers should first contact <a href="mailto:{{contact_email}}">{{contact_email}}</a> so the store can attempt to resolve a complaint directly. Where a governing region is configured, applicable disputes are handled under the laws and procedures of {{governing_region}}, subject to mandatory consumer protections.</p>

<h2>5. Business Operations</h2>
<p>{{store_name}} operates an online retail store focused on {{product_term}} as described by: {{product_niche}}.</p>

<h2>6. Product Safety</h2>
<p>{{niche_safety_clause}}</p>

<h2>7. Related Policies</h2>
<p><a href="/policies/terms-of-service">Terms of Service</a> - <a href="/policies/privacy-policy">Privacy Policy</a> - <a href="/policies/shipping-policy">Shipping Policy</a> - <a href="/policies/refund-policy">Refund & Return Policy</a> - <a href="/pages/order-cancellation-policy">Order Cancellation Policy</a> - <a href="/policies/payment-policy">Payment Policy</a> - <a href="/pages/warranty-policy">Warranty Policy</a></p>

<h2>Contact Us</h2>
<p>Email: <a href="mailto:{{contact_email}}">{{contact_email}}</a> | Phone: <a href="tel:{{phone}}">{{phone}}</a> | Business Hours: {{support_hours}} ({{support_timezone}})</p>
""",
    "privacy_policy": """<p><strong>Last updated:</strong> {{current_year}}</p>
<p>{{store_name}} operates {{domain_name}} and uses Shopify and other configured service providers to deliver the online store. This policy explains the categories of personal information that may be processed when customers browse, communicate with the store or complete a transaction.</p>

<h2>Personal Information We Collect or Process</h2>
<p>Depending on the customer interaction, information may include contact details, billing and shipping details, transaction records, account information, support messages, device/network data and usage information.</p>

<h2>Personal Information Sources</h2>
<p>Information may come directly from customers, automatically from website interactions and cookies, from Shopify, from service providers acting for the store, and from third parties where permitted and relevant to the service.</p>

<h2>How We Use Your Personal Information</h2>
<ul>
  <li>Provide, operate and improve the store and customer service.</li>
  <li>Process orders, payments, shipping, returns, cancellations and account functions.</li>
  <li>Communicate transactional and support information.</li>
  <li>Protect the store and customers against fraud, abuse and security incidents.</li>
  <li>Send marketing only where permitted and subject to available opt-out controls.</li>
  <li>Comply with legal obligations and enforce store terms.</li>
</ul>

<h2>How We Disclose Personal Information</h2>
<p>Information may be shared with Shopify, payment processors, shipping/fulfillment providers, IT and hosting vendors, analytics or support providers, and other service partners that need the information to perform a legitimate store function. Information may also be disclosed when required by law or in connection with a business transaction.</p>

<h2>Relationship with Shopify</h2>
<p>The store is hosted or supported by Shopify. Information submitted through the storefront may be processed by Shopify in order to operate, secure and improve the commerce services. Shopify's own privacy materials govern Shopify's independent processing activities.</p>

<h2>Third Party Websites and Links</h2>
<p>External links may lead to websites controlled by third parties. Their privacy and security practices are governed by their own policies, and {{store_name}} is not responsible for third-party content solely because a link appears on the store.</p>

<h2>Children's Data</h2>
<p>The store is not intended to knowingly collect personal information from children below the age at which they may independently consent under applicable law. A parent or guardian may contact <a href="mailto:{{contact_email}}">{{contact_email}}</a> regarding information they believe was provided by a child.</p>

<h2>Security and Retention of Your Information</h2>
<p>Reasonable administrative and technical safeguards are used, but no transmission or storage method can be guaranteed perfectly secure. Information is retained only for as long as reasonably needed for store operations, legal obligations, disputes, security and recordkeeping.</p>

<h2>Your Rights and Choices</h2>
<p>Depending on location, customers may have rights to request access, correction, deletion, portability or certain opt-outs. These rights can be exercised where applicable by contacting <a href="mailto:{{contact_email}}">{{contact_email}}</a>. Identity verification may be required before a request is completed.</p>

<h2>Complaints</h2>
<p>Privacy questions or complaints should first be sent to <a href="mailto:{{contact_email}}">{{contact_email}}</a>. Customers may also have a right to contact a local data-protection authority depending on where they live.</p>

<h2>International Transfers</h2>
<p>Service providers may process information in countries other than the customer's country. We ensure data transfers comply with applicable privacy laws.</p>

<h2>Changes to This Privacy Policy</h2>
<p>This policy may be updated to reflect operational, legal or service changes. The current version should remain available at the same public URL and display an updated effective date.</p>

<h2>Contact</h2>
<ul>
  <li><strong>Business Name:</strong> {{legal_business_name}}</li>
  <li><strong>Address:</strong> {{store_address}}</li>
  <li><strong>Email:</strong> <a href="mailto:{{contact_email}}">{{contact_email}}</a></li>
  <li><strong>Phone:</strong> <a href="tel:{{phone}}">{{phone}}</a></li>
  <li><strong>Business Hours:</strong> {{support_hours}} ({{support_timezone}})</li>
</ul>
""",
    "payment_policy": """<p>{{store_name}} provides checkout through the payment methods actually enabled for the store. This policy explains accepted methods, authorization, pricing and billing handling.</p>
<p>Read this together with Terms of Service, Refund & Return Policy, Order Cancellation Policy and Privacy Policy.</p>

<h2>1. Accepted Payment Methods</h2>
<p>{{payment_methods}}.</p>

<h2>2. Payment Security & Encryption</h2>
<p>Checkout is provided through {{payment_processor}} and Shopify where applicable. Payment data should be transmitted using HTTPS/TLS and handled by the configured payment provider. We do not store your full card data on our servers.</p>

<h2>3. Order Acceptance & When You Are Charged</h2>
<p>Placing an order is a request to purchase. If a payment cannot be authorized, the order may not proceed.</p>

<h2>4. Prices, Currency & Sales Tax</h2>
<p>Store prices are shown in {{currency}} unless another currency is presented at checkout. Taxes are applied where required. Bank conversion or foreign-transaction fees, if any, are set by the customer's payment provider rather than {{store_name}}.</p>

<h2>5. Billing Information & Verification</h2>
<p>Customers should provide accurate billing information. Transactions may be reviewed for security or fraud prevention, and an order may be delayed or cancelled if payment cannot be verified.</p>

<h2>6. Pricing Errors</h2>
<p>{{store_name}} may correct genuine pricing, description or promotional errors. If an order cannot be fulfilled because of a material error, the customer should be notified and any captured amount returned to the original payment method.</p>

<h2>7. Refunds, Cancellations & Chargebacks</h2>
<p>Approved refunds are sent to the original payment method within {{refund_processing_time}}. Cancellation requests follow the {{cancellation_window_hours}}-hour configured window where applicable. Customers should contact <a href="mailto:{{contact_email}}">{{contact_email}}</a> about billing issues so the store can investigate promptly.</p>

<h2>8. Relationship with Shopify</h2>
<p>Where Shopify powers the storefront or checkout, Shopify supplies commerce infrastructure, but the sale remains between the customer and {{store_name}} unless the transaction documentation states otherwise.</p>

<h2>9. Governing Law & Changes to This Policy</h2>
<p>This policy forms part of the store terms. The current policy version remains available at its public URL.</p>

<h2>Contact Information</h2>
<p>{{store_name}} | {{store_address}} | <a href="mailto:{{contact_email}}">{{contact_email}}</a> | <a href="tel:{{phone}}">{{phone}}</a> | {{support_hours}} ({{support_timezone}})</p>
""",
    "shipping_policy": """<p>This policy explains where {{store_name}} ships, what delivery may cost, how long orders normally take and what customers should do if a shipment has a problem.</p>

<h2>1. Shipping Destinations</h2>
<p>Orders are currently shipped to: {{shipping_destination}}.</p>

<h2>2. Shipping Cost</h2>
<p>{{shipping_cost_text}}.</p>

<h2>3. Order Processing & Transit Time</h2>
<ul>
  <li><strong>Order Cut-off Time:</strong> {{shipping_cutoff}}</li>
  <li><strong>Order Handling Time:</strong> {{handling_time}}</li>
  <li><strong>Transit Time:</strong> {{transit_time}}</li>
  <li><strong>Total Estimated Delivery Time:</strong> {{estimated_delivery_time}}</li>
</ul>
<p>Business days are Monday through Friday, excluding public holidays.</p>

<h2>4. Order Tracking</h2>
<p>After dispatch, customers should receive available tracking information. Tracking may require {{tracking_update_time}} to update after the carrier first receives the shipment.</p>

<h2>5. Shipping Method</h2>
<p>We use reliable carriers to ensure your order arrives safely.</p>

<h2>6. Address Changes & Cancellations</h2>
<p>Customers should contact <a href="mailto:{{contact_email}}">{{contact_email}}</a> within {{cancellation_window_hours}} hours if they need to request an address change or cancellation. Changes cannot be guaranteed once fulfillment or carrier handoff has progressed.</p>

<h2>7. Damaged or Lost Packages</h2>
<p>Customers should contact support promptly if a shipment arrives damaged or appears lost. {{store_name}} should investigate with the carrier and apply the remedy described by the Refund & Return Policy and any applicable consumer rights.</p>

<h2>Related Policies</h2>
<p><a href="/policies/refund-policy">Refund & Return Policy</a> - <a href="/pages/track-order">Track Order</a> - <a href="/policies/privacy-policy">Privacy Policy</a> - <a href="/policies/terms-of-service">Terms of Service</a> - <a href="/pages/contact-us">Contact Us</a></p>

<h2>Contact Information</h2>
<p>{{store_name}} | {{store_address}} | <a href="mailto:{{contact_email}}">{{contact_email}}</a> | <a href="tel:{{phone}}">{{phone}}</a> | {{support_hours}} ({{support_timezone}})</p>
""",
    "refund_return_policy": """<p>{{store_name}} wants customers to understand return eligibility before purchasing. This policy defines the return window, condition rules, return process, fees, exchanges and refund timing.</p>
<p>Read this with Warranty Policy, Order Cancellation Policy and Shipping Policy.</p>

<h2>1. {{return_window_days}}-Day Return Window</h2>
<p>Eligible return requests must be submitted within {{return_window_days}} days from the policy's configured start point, normally delivery.</p>

<h2>2. Return Eligibility</h2>
<p>Returned goods should be in the condition required by the store policy, with relevant packaging, accessories and proof of purchase. {{niche_return_restrictions}}</p>

<h2>3. Niche-Specific Restricted or Used Products</h2>
<p>{{niche_return_restrictions}}.</p>

<h2>4. How to Return ({{return_method}})</h2>
<p>Customers begin a return by contacting <a href="mailto:{{contact_email}}">{{contact_email}}</a> with their order number and reason for return. The store provides authorization and the correct return instructions. Unrequested parcels may be refused where lawful and clearly disclosed.</p>

<h2>5. Return Shipping Costs</h2>
<p>{{return_fee_text}}. Restocking fee: {{restocking_fee_text}}.</p>

<h2>6. Damaged, Wrong Products, or Issues</h2>
<p>Customers should inspect orders after delivery and contact support promptly about damaged, defective or incorrect items. Transit damage should also be handled consistently with the Shipping Policy.</p>

<h2>7. Exchanges</h2>
<p>{{exchange_policy_text}}</p>

<h2>8. Refunds</h2>
<p>After any required inspection, approved refunds are issued to the original payment method within {{refund_processing_time}}. The customer's bank or card issuer may take additional time to display the credit.</p>

<h2>9. Non-Returnable Items</h2>
<p>{{non_returnable_items}}.</p>

<h2>10. Cancellations</h2>
<p>If an order has not progressed too far, the customer may request cancellation under the Order Cancellation Policy within {{cancellation_window_hours}} hours. After shipment, the return policy normally applies instead.</p>

<h2>Related Policies</h2>
<p><a href="/policies/shipping-policy">Shipping Policy</a> - <a href="/pages/track-order">Track Order</a> - <a href="/pages/warranty-policy">Warranty Policy</a> - <a href="/pages/order-cancellation-policy">Order Cancellation Policy</a> - <a href="/policies/privacy-policy">Privacy Policy</a> - <a href="/policies/terms-of-service">Terms of Service</a> - <a href="/pages/contact-us">Contact Us</a></p>

<h2>Contact Information</h2>
<p>{{store_name}} | {{store_address}} | <a href="mailto:{{contact_email}}">{{contact_email}}</a> | <a href="tel:{{phone}}">{{phone}}</a> | {{support_hours}} ({{support_timezone}})</p>
""",
    "order_cancellation_policy": """<p>{{store_name}} may begin processing orders soon after purchase. This policy explains when a cancellation can be requested, how the request is submitted and what happens after the cancellation window has closed.</p>

<h2>1. Cancellation Window</h2>
<p>A customer may request cancellation within {{cancellation_window_hours}} hours of placing the order, provided the order has not reached a processing or shipping stage that makes cancellation impractical.</p>

<h2>2. How to Request a Cancellation</h2>
<p>Send the request to <a href="mailto:{{contact_email}}">{{contact_email}}</a> with the order number and a clear cancellation request. A request is not confirmed until {{store_name}} sends written confirmation.</p>

<h2>3. Orders That Have Already Shipped</h2>
<p>After dispatch, an order can no longer be treated as a pre-shipment cancellation. The customer should follow the Refund & Return Policy after delivery, subject to return eligibility.</p>

<h2>4. Refunds for Cancelled Orders</h2>
<p>When a cancellation is successfully confirmed, any captured eligible amount is returned to the original payment method within {{refund_processing_time}}. External payment providers may require additional posting time.</p>

<h2>5. Items That Cannot Be Cancelled</h2>
<p>{{non_cancellable_items}}.</p>

<h2>6. Cancellations by {{store_name}}</h2>
<p>{{store_name}} may cancel an order when an item is unavailable, a material pricing/listing error exists, payment cannot be verified, the delivery address is unsupported, or another legitimate fulfillment issue prevents the sale. Any captured amount for the cancelled portion will be refunded.</p>

<h2>7. Modifications Instead of Cancellation</h2>
<p>Customers seeking an address or product change should contact support within the same {{cancellation_window_hours}}-hour window. A modification is not guaranteed; cancellation and a new order may be required.</p>

<h2>8. Governing Law</h2>
<p>Where configured, this policy is governed by {{governing_region}}, subject to non-waivable consumer protections. Related personal information is handled under the Privacy Policy.</p>

<h2>9. Changes to This Policy</h2>
<p>The current version of this policy remains available at its public URL. Material operational changes should be reflected consistently in checkout, FAQ and Merchant Center where relevant.</p>

<h2>Related Policies</h2>
<p><a href="/policies/refund-policy">Refund & Return Policy</a> - <a href="/policies/shipping-policy">Shipping Policy</a> - <a href="/pages/track-order">Track Order</a> - <a href="/policies/privacy-policy">Privacy Policy</a> - <a href="/policies/terms-of-service">Terms of Service</a> - <a href="/pages/legal-notice">Legal Notice</a> - <a href="/pages/contact-us">Contact Us</a></p>

<h2>Contact Information</h2>
<p>{{store_name}} | {{store_address}} | <a href="mailto:{{contact_email}}">{{contact_email}}</a> | <a href="tel:{{phone}}">{{phone}}</a> | {{support_hours}} ({{support_timezone}})</p>
""",
    "warranty_policy": """<p>{{warranty_intro}}</p>

<h2>1. What Is Covered</h2>
<p>Covered defects are limited to the defects and product categories actually included in the store's warranty configuration.</p>

<h2>2. Our Remedy</h2>
<p>For an approved claim, {{store_name}} may repair, replace or provide another remedy stated in the configured warranty.</p>

<h2>3. What Is Not Covered</h2>
<p>{{warranty_exclusions}}.</p>

<h2>4. How to Make a Warranty Claim</h2>
<p>Email <a href="mailto:{{contact_email}}">{{contact_email}}</a> with the order number, proof of purchase, product identification, a description of the fault and supporting media where useful.</p>

<h2>5. Shipping Costs on Warranty Claims</h2>
<p>{{warranty_shipping_cost_text}}.</p>

<h2>6. Warranty vs. Returns - Which Applies?</h2>
<p>Returns address purchase suitability and eligible post-delivery returns within {{return_window_days}} days. Cancellation addresses pre-fulfillment requests within {{cancellation_window_hours}} hours. Warranty addresses covered defects during {{warranty_period}}.</p>

<h2>7. Transferability</h2>
<p>{{warranty_transferability_text}}.</p>

<h2>8. Limitations and Your Statutory Rights</h2>
<p>The limited warranty does not remove consumer rights that cannot legally be excluded.</p>

<h2>9. Governing Law & Changes to This Policy</h2>
<p>Where configured, this policy is governed by {{governing_region}}. Claims are assessed under the terms applicable at the time of purchase.</p>

<h2>Related Policies</h2>
<p><a href="/policies/refund-policy">Refund & Return Policy</a> - <a href="/policies/shipping-policy">Shipping Policy</a> - <a href="/pages/order-cancellation-policy">Order Cancellation Policy</a> - <a href="/pages/track-order">Track Order</a> - <a href="/policies/privacy-policy">Privacy Policy</a> - <a href="/policies/terms-of-service">Terms of Service</a> - <a href="/pages/legal-notice">Legal Notice</a> - <a href="/pages/contact-us">Contact Us</a></p>

<h2>Contact Information</h2>
<p>{{store_name}} | {{store_address}} | <a href="mailto:{{contact_email}}">{{contact_email}}</a> | <a href="tel:{{phone}}">{{phone}}</a> | {{support_hours}} ({{support_timezone}})</p>
""",
    "terms_of_service": """
<h2>OVERVIEW</h2>
<p>These Terms of Service govern use of {{domain_name}} and purchases from {{store_name}}. The terms "we", "us" and "our" refer to {{store_name}}. Shopify may provide the ecommerce platform, while the merchant remains responsible for the sale unless otherwise stated.</p>

<h2>SECTION 1 - ACCESS AND ACCOUNT</h2>
<p>Customers must provide accurate information and use the store lawfully. Where an account is created, the customer is responsible for safeguarding credentials and activity under that account.</p>

<h2>SECTION 2 - OUR PRODUCTS</h2>
<p>Product pages aim to describe items accurately, but display settings can affect appearance. Specifications, availability and descriptions may change, and quantities may be limited where appropriate.</p>

<h2>SECTION 3 - ORDERS</h2>
<p>Submitting an order is an offer to purchase. {{store_name}} may accept, decline or cancel an order for legitimate reasons such as availability, verification or material listing errors. Cancellation and returns are handled under their dedicated policies.</p>

<h2>SECTION 4 - PRICES AND BILLING</h2>
<p>Prices are shown in {{currency}} unless checkout indicates otherwise. Customers must provide current billing and payment information. Taxes, shipping and other charges are disclosed where applicable.</p>

<h2>SECTION 5 - SHIPPING AND DELIVERY</h2>
<p>Delivery estimates are not guarantees and may be affected by carrier or external conditions. Shipping details are governed by the Shipping Policy, including {{handling_time}} handling and {{transit_time}} estimated transit where configured.</p>

<h2>SECTION 6 - INTELLECTUAL PROPERTY</h2>
<p>The store's original branding, text, graphics, layout and owned media are protected by applicable intellectual-property law. Personal shopping use does not grant a right to republish or commercially exploit protected content.</p>

<h2>SECTION 7 - OPTIONAL TOOLS</h2>
<p>Third-party tools may be made available through the store. Their use may be subject to separate third-party terms, and customers should review those terms before using the tool.</p>

<h2>SECTION 8 - THIRD-PARTY LINKS</h2>
<p>Links may lead to third-party websites that {{store_name}} does not control. Customers should review the third party's own policies before transacting or sharing information.</p>

<h2>SECTION 9 - RELATIONSHIP WITH SHOPIFY</h2>
<p>Shopify may provide storefront, checkout and commerce infrastructure. Purchases are made from {{store_name}}, and Shopify is not the merchant unless checkout documentation explicitly states otherwise.</p>

<h2>SECTION 10 - PRIVACY POLICY</h2>
<p>Personal information is handled according to the Privacy Policy and applicable Shopify privacy information. Customers should review those documents before using the store.</p>

<h2>SECTION 11 - FEEDBACK</h2>
<p>If customers voluntarily submit reviews, suggestions or other feedback, they grant the store the rights reasonably necessary to display and use that feedback for store operations and promotion, subject to applicable law and platform rules.</p>

<h2>SECTION 12 - ERRORS, INACCURACIES AND OMISSIONS</h2>
<p>{{store_name}} may correct genuine typographical, pricing, availability or descriptive errors. When an error materially affects an order, the store may contact the customer, correct the information or cancel/refund as appropriate.</p>

<h2>SECTION 13 - PROHIBITED USES</h2>
<p>Customers may not use the store for unlawful activity, infringement, fraud, abusive conduct, malware distribution, unauthorized data collection, security circumvention or other conduct that harms the service or other users.</p>

<h2>SECTION 14 - AGENTS</h2>
<p>Automated agents that access the store must comply with applicable technical restrictions, robots directives, platform terms and any identification requirements imposed by the store or service providers. </p>

<h2>SECTION 15 - TERMINATION</h2>
<p>{{store_name}} may restrict or terminate access where permitted when these Terms are materially violated. Clauses that logically survive termination, such as intellectual-property and liability provisions, continue to apply.</p>

<h2>SECTION 16 - DISCLAIMER OF WARRANTIES</h2>
<p>To the extent permitted by law, the website and services are provided without guarantees beyond express product or statutory warranties. Nothing here removes rights that cannot legally be excluded.</p>

<h2>SECTION 17 - LIMITATION OF LIABILITY</h2>
<p>To the fullest extent permitted by applicable law, liability for indirect or consequential losses may be limited. </p>

<h2>SECTION 18 - INDEMNIFICATION</h2>
<p>Where legally enforceable, a user may be responsible for losses arising from their material breach of these Terms, unlawful use of the service or infringement of third-party rights.</p>

<h2>SECTION 19 - SEVERABILITY</h2>
<p>If one provision is found unenforceable, the remaining provisions continue to apply to the extent permitted by law.</p>

<h2>SECTION 20 - WAIVER; ENTIRE AGREEMENT</h2>
<p>A failure to enforce a provision is not automatically a waiver. These Terms and incorporated store policies form the agreement governing use of the store, subject to mandatory law.</p>

<h2>SECTION 21 - ASSIGNMENT</h2>
<p>Customers may not transfer obligations under these Terms where prohibited by the agreement or law. {{store_name}} may transfer its rights and obligations as part of a lawful business transfer or restructuring where permitted.</p>

<h2>SECTION 22 - GOVERNING LAW</h2>
<p>Where configured, the governing region is {{governing_region}}. Mandatory consumer protections and jurisdiction rules continue to apply where they override a contractual choice of law.</p>

<h2>SECTION 23 - HEADINGS</h2>
<p>Section headings are included for organization and do not change the meaning of the Terms.</p>

<h2>SECTION 24 - CHANGES TO TERMS OF SERVICE</h2>
<p>The current Terms remain available at this public URL. Material changes should be posted with an updated effective date and any notice required by law.</p>

<h2>SECTION 25 - CONTACT INFORMATION</h2>
<ul>
  <li><strong>Business Name:</strong> {{legal_business_name}}</li>
  <li><strong>Address:</strong> {{store_address}}</li>
  <li><strong>Email:</strong> <a href="mailto:{{contact_email}}">{{contact_email}}</a></li>
  <li><strong>Phone:</strong> <a href="tel:{{phone}}">{{phone}}</a></li>
  <li><strong>Business Hours:</strong> {{support_hours}} ({{support_timezone}})</li>
</ul>
""",
}
