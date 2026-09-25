# Static Templates for 4GMC Pages & Policies

ABOUT_US = [
    """
<h2>Welcome to {{brand_name}}</h2>
<p>At {{brand_name}}, our mission is to provide you with the best {{product_term}}. We understand that {{customer_need}} is important to you, which is why we offer {{niche_description}}.</p>
<p>Founded with a passion for quality, {{brand_name}} operates online to serve customers across {{shipping_regions}}. We believe in transparent pricing, reliable shipping, and dedicated support.</p>
<p>If you have any questions about our {{product_term}}, please do not hesitate to reach out to us at <a href="mailto:{{support_email}}">{{support_email}}</a>.</p>
    """,
    """
<h2>Our Story</h2>
<p>Welcome to {{brand_name}}, your trusted source for {{product_term}}. We are dedicated to giving you the very best experience, with a focus on dependability, customer service, and uniqueness.</p>
<p>When we first started out, our passion for {{niche_label}} drove us to start our own business. Now, we serve customers everywhere and are thrilled to be a part of the fair trade wing of the industry.</p>
<p>We hope you enjoy our products as much as we enjoy offering them to you. For inquiries, you can contact us during our support hours ({{support_hours}}) at {{support_email}}.</p>
    """,
    """
<h2>About {{brand_name}}</h2>
<p>{{brand_name}} is committed to excellence in the {{niche_label}} market. Our team carefully selects the finest {{product_term}} to ensure that your experience is nothing short of exceptional.</p>
<p>Our operations are centered around making {{customer_need}} easier and more enjoyable. From seamless browsing on our secure platform to fast delivery to your door, we prioritize your satisfaction.</p>
<p>Thank you for choosing {{brand_name}}. We look forward to serving you.</p>
    """
]

CONTACT_US = [
    """
<div class="contact-page-layout" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 48px; align-items: start; margin-top: 16px; margin-bottom: 32px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1f2937; line-height: 1.6;">
  <div class="contact-info-column" style="display: flex; flex-direction: column; gap: 24px;">
    <p style="font-size: 1.05rem; color: #4b5563; margin: 0; line-height: 1.5;">Have a question about your order? We are here to help!</p>
    <div>
      <h2 style="font-size: 1.25rem; font-weight: 700; color: #111827; margin: 0 0 12px 0;">Contact Information</h2>
      <div style="display: flex; flex-direction: column; gap: 8px; font-size: 0.95rem;">
        <p style="margin: 0;"><strong>Store Name:</strong> {{brand_name}}</p>
        <p style="margin: 0;"><strong>Email:</strong> <a href="mailto:{{support_email}}" style="color: #2251dc; text-decoration: underline;">{{support_email}}</a></p>
        <p style="margin: 0;"><strong>Phone:</strong> <a href="tel:{{phone}}" style="color: #2251dc; text-decoration: underline;">{{phone}}</a></p>
        <p style="margin: 0;"><strong>Address:</strong> {{business_address}}, {{business_city}}, {{business_state}} {{business_zip}}, {{business_country}}</p>
      </div>
    </div>
    <div>
      <h2 style="font-size: 1.25rem; font-weight: 700; color: #111827; margin: 0 0 12px 0;">Customer Support Hours</h2>
      <div style="display: flex; flex-direction: column; gap: 6px; font-size: 0.95rem;">
        <p style="margin: 0;">{{support_hours}} ({{support_timezone}})</p>
      </div>
    </div>
  </div>
  <div class="contact-form-column" style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 12px; padding: 32px 28px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
    <h2 style="margin: 0 0 20px 0; font-size: 1.5rem; font-weight: 700; color: #111827;">Send Us a Message</h2>
    <form method="post" action="/contact#contact_form" id="contact_form" accept-charset="UTF-8" class="contact-form" style="display: flex; flex-direction: column; gap: 16px;">
      <input type="hidden" name="form_type" value="contact">
      <input type="hidden" name="utf8" value="✓">
      <div><label for="ContactFormName" style="display: block; font-weight: 600; margin-bottom: 6px; font-size: 0.9rem; color: #374151;">Name</label><input type="text" id="ContactFormName" name="contact[name]" required style="width: 100%; box-sizing: border-box; padding: 12px 14px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 1rem; background-color: #ffffff;"></div>
      <div><label for="ContactFormEmail" style="display: block; font-weight: 600; margin-bottom: 6px; font-size: 0.9rem; color: #374151;">Email</label><input type="email" id="ContactFormEmail" name="contact[email]" required style="width: 100%; box-sizing: border-box; padding: 12px 14px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 1rem; background-color: #ffffff;"></div>
      <div><label for="ContactFormMessage" style="display: block; font-weight: 600; margin-bottom: 6px; font-size: 0.9rem; color: #374151;">Message</label><textarea id="ContactFormMessage" name="contact[body]" rows="5" required style="width: 100%; box-sizing: border-box; padding: 12px 14px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 1rem; font-family: inherit; resize: vertical; background-color: #ffffff;"></textarea></div>
      <button type="submit" style="width: 100%; padding: 14px 20px; background-color: #2251dc; color: #ffffff; border: none; border-radius: 6px; font-weight: 700; font-size: 0.95rem; letter-spacing: 0.05em; text-transform: uppercase; cursor: pointer; transition: opacity 0.2s ease;">SEND MESSAGE</button>
    </form>
  </div>
</div>
    """,
    """
<div class="contact-page-layout" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 48px; align-items: start; margin-top: 16px; margin-bottom: 32px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1f2937; line-height: 1.6;">
  <div class="contact-info-column" style="display: flex; flex-direction: column; gap: 24px;">
    <p style="font-size: 1.05rem; color: #4b5563; margin: 0; line-height: 1.5;">Need assistance? Our support team is ready to assist you.</p>
    <div>
      <h2 style="font-size: 1.25rem; font-weight: 700; color: #111827; margin: 0 0 12px 0;">Contact Information</h2>
      <div style="display: flex; flex-direction: column; gap: 8px; font-size: 0.95rem;">
        <p style="margin: 0;"><strong>Store Name:</strong> {{brand_name}}</p>
        <p style="margin: 0;"><strong>Email:</strong> <a href="mailto:{{support_email}}" style="color: #2251dc; text-decoration: underline;">{{support_email}}</a></p>
        <p style="margin: 0;"><strong>Phone:</strong> <a href="tel:{{phone}}" style="color: #2251dc; text-decoration: underline;">{{phone}}</a></p>
        <p style="margin: 0;"><strong>Address:</strong> {{business_address}}, {{business_city}}, {{business_state}} {{business_zip}}, {{business_country}}</p>
      </div>
    </div>
    <div>
      <h2 style="font-size: 1.25rem; font-weight: 700; color: #111827; margin: 0 0 12px 0;">Customer Support Hours</h2>
      <div style="display: flex; flex-direction: column; gap: 6px; font-size: 0.95rem;">
        <p style="margin: 0;">{{support_hours}} ({{support_timezone}})</p>
      </div>
    </div>
  </div>
  <div class="contact-form-column" style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 12px; padding: 32px 28px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
    <h2 style="margin: 0 0 20px 0; font-size: 1.5rem; font-weight: 700; color: #111827;">Send Us a Message</h2>
    <form method="post" action="/contact#contact_form" id="contact_form" accept-charset="UTF-8" class="contact-form" style="display: flex; flex-direction: column; gap: 16px;">
      <input type="hidden" name="form_type" value="contact">
      <input type="hidden" name="utf8" value="✓">
      <div><label for="ContactFormName" style="display: block; font-weight: 600; margin-bottom: 6px; font-size: 0.9rem; color: #374151;">Name</label><input type="text" id="ContactFormName" name="contact[name]" required style="width: 100%; box-sizing: border-box; padding: 12px 14px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 1rem; background-color: #ffffff;"></div>
      <div><label for="ContactFormEmail" style="display: block; font-weight: 600; margin-bottom: 6px; font-size: 0.9rem; color: #374151;">Email</label><input type="email" id="ContactFormEmail" name="contact[email]" required style="width: 100%; box-sizing: border-box; padding: 12px 14px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 1rem; background-color: #ffffff;"></div>
      <div><label for="ContactFormMessage" style="display: block; font-weight: 600; margin-bottom: 6px; font-size: 0.9rem; color: #374151;">Message</label><textarea id="ContactFormMessage" name="contact[body]" rows="5" required style="width: 100%; box-sizing: border-box; padding: 12px 14px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 1rem; font-family: inherit; resize: vertical; background-color: #ffffff;"></textarea></div>
      <button type="submit" style="width: 100%; padding: 14px 20px; background-color: #2251dc; color: #ffffff; border: none; border-radius: 6px; font-weight: 700; font-size: 0.95rem; letter-spacing: 0.05em; text-transform: uppercase; cursor: pointer; transition: opacity 0.2s ease;">SEND MESSAGE</button>
    </form>
  </div>
</div>
    """,
    """
<div class="contact-page-layout" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 48px; align-items: start; margin-top: 16px; margin-bottom: 32px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1f2937; line-height: 1.6;">
  <div class="contact-info-column" style="display: flex; flex-direction: column; gap: 24px;">
    <p style="font-size: 1.05rem; color: #4b5563; margin: 0; line-height: 1.5;">Get in touch with us! We'd love to hear from you.</p>
    <div>
      <h2 style="font-size: 1.25rem; font-weight: 700; color: #111827; margin: 0 0 12px 0;">Contact Information</h2>
      <div style="display: flex; flex-direction: column; gap: 8px; font-size: 0.95rem;">
        <p style="margin: 0;"><strong>Store Name:</strong> {{brand_name}}</p>
        <p style="margin: 0;"><strong>Email:</strong> <a href="mailto:{{support_email}}" style="color: #2251dc; text-decoration: underline;">{{support_email}}</a></p>
        <p style="margin: 0;"><strong>Phone:</strong> <a href="tel:{{phone}}" style="color: #2251dc; text-decoration: underline;">{{phone}}</a></p>
        <p style="margin: 0;"><strong>Address:</strong> {{business_address}}, {{business_city}}, {{business_state}} {{business_zip}}, {{business_country}}</p>
      </div>
    </div>
    <div>
      <h2 style="font-size: 1.25rem; font-weight: 700; color: #111827; margin: 0 0 12px 0;">Customer Support Hours</h2>
      <div style="display: flex; flex-direction: column; gap: 6px; font-size: 0.95rem;">
        <p style="margin: 0;">{{support_hours}} ({{support_timezone}})</p>
      </div>
    </div>
  </div>
  <div class="contact-form-column" style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 12px; padding: 32px 28px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
    <h2 style="margin: 0 0 20px 0; font-size: 1.5rem; font-weight: 700; color: #111827;">Send Us a Message</h2>
    <form method="post" action="/contact#contact_form" id="contact_form" accept-charset="UTF-8" class="contact-form" style="display: flex; flex-direction: column; gap: 16px;">
      <input type="hidden" name="form_type" value="contact">
      <input type="hidden" name="utf8" value="✓">
      <div><label for="ContactFormName" style="display: block; font-weight: 600; margin-bottom: 6px; font-size: 0.9rem; color: #374151;">Name</label><input type="text" id="ContactFormName" name="contact[name]" required style="width: 100%; box-sizing: border-box; padding: 12px 14px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 1rem; background-color: #ffffff;"></div>
      <div><label for="ContactFormEmail" style="display: block; font-weight: 600; margin-bottom: 6px; font-size: 0.9rem; color: #374151;">Email</label><input type="email" id="ContactFormEmail" name="contact[email]" required style="width: 100%; box-sizing: border-box; padding: 12px 14px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 1rem; background-color: #ffffff;"></div>
      <div><label for="ContactFormMessage" style="display: block; font-weight: 600; margin-bottom: 6px; font-size: 0.9rem; color: #374151;">Message</label><textarea id="ContactFormMessage" name="contact[body]" rows="5" required style="width: 100%; box-sizing: border-box; padding: 12px 14px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 1rem; font-family: inherit; resize: vertical; background-color: #ffffff;"></textarea></div>
      <button type="submit" style="width: 100%; padding: 14px 20px; background-color: #2251dc; color: #ffffff; border: none; border-radius: 6px; font-weight: 700; font-size: 0.95rem; letter-spacing: 0.05em; text-transform: uppercase; cursor: pointer; transition: opacity 0.2s ease;">SEND MESSAGE</button>
    </form>
  </div>
</div>
    """,
]

FAQ = [
    """
<h2>Frequently Asked Questions</h2>
<h3>Orders & Payments</h3>
<p><strong>What payment methods do you accept?</strong><br>We accept {{payment_methods}}. All prices are in {{currency}}.</p>
<p><strong>Can I cancel my order?</strong><br>Yes, order cancellations are permitted within {{cancellation_window}}.</p>
<h3>Shipping & Delivery</h3>
<p><strong>Where do you ship?</strong><br>We currently ship to {{shipping_regions}}.</p>
<p><strong>How long does shipping take?</strong><br>Orders are processed in {{processing_time}}. Transit time is typically {{transit_time}}, resulting in an estimated delivery time of {{estimated_delivery_time}}.</p>
<p><strong>How much is shipping?</strong><br>Shipping cost is {{shipping_cost}}. We offer free shipping: {{free_shipping}}.</p>
<h3>Returns & Refunds</h3>
<p><strong>What is your return policy?</strong><br>We accept returns within {{return_window}} of delivery. Please contact us to initiate a return.</p>
<p><strong>How do I return an item?</strong><br>Returns are processed {{return_method}}. Return shipping costs are {{return_shipping_cost}}.</p>
<p><strong>When will I receive my refund?</strong><br>Once approved, refunds are processed within {{refund_processing_time}}.</p>
<h3>Contact Us</h3>
<p>If you need further assistance, email us at <a href="mailto:{{support_email}}">{{support_email}}</a> or call {{phone}}. We are available {{support_hours}} ({{support_timezone}}).</p>
    """,
    """
<h2>Help Center (FAQ)</h2>
<h3>Payment & Cancellations</h3>
<ul>
<li><strong>Accepted payments:</strong> We support {{payment_methods}} and process all transactions in {{currency}}.</li>
<li><strong>Order cancellations:</strong> If you change your mind, you can cancel your order within {{cancellation_window}}.</li>
</ul>
<h3>Shipping Information</h3>
<ul>
<li><strong>Shipping regions:</strong> Our store proudly ships to {{shipping_regions}}.</li>
<li><strong>Timelines:</strong> Processing requires {{processing_time}}, followed by a transit time of {{transit_time}}. Expected total time is {{estimated_delivery_time}}.</li>
<li><strong>Costs:</strong> Our standard shipping fee is {{shipping_cost}}. Free shipping availability: {{free_shipping}}.</li>
</ul>
<h3>Return Policies</h3>
<ul>
<li><strong>Return window:</strong> You have {{return_window}} to request a return.</li>
<li><strong>Process:</strong> Send the item back {{return_method}}. Please note that shipping costs are {{return_shipping_cost}}.</li>
<li><strong>Refund speed:</strong> Expect your refund in {{refund_processing_time}} after we inspect your return.</li>
</ul>
<h3>Need more help?</h3>
<p>Reach out to us via email at <a href="mailto:{{support_email}}">{{support_email}}</a> or by phone at {{phone}}. Our team operates {{support_hours}} ({{support_timezone}}).</p>
    """,
    """
<h2>Questions & Answers</h2>
<p>Find answers to our most common questions below.</p>
<h3>Purchasing</h3>
<p>We process transactions in {{currency}} using secure payment gateways. Our supported methods include {{payment_methods}}.<br>If you placed an order by mistake, you have a grace period of {{cancellation_window}} to cancel it.</p>
<h3>Delivery</h3>
<p>We deliver to {{shipping_regions}}. We charge {{shipping_cost}} for standard shipping (Free shipping offered: {{free_shipping}}).<br>Please allow {{processing_time}} for us to prepare your package. Shipping itself takes {{transit_time}}, meaning you should receive your items in {{estimated_delivery_time}}.</p>
<h3>Returns</h3>
<p>Items can be returned within {{return_window}} of receipt. To do so, please return the product {{return_method}}. Be advised that the return shipping cost falls under {{return_shipping_cost}}.<br>Refunds take approximately {{refund_processing_time}} to process once your item is verified by our team.</p>
<h3>Customer Service</h3>
<p>If your question isn't answered here, call us at {{phone}} or email <a href="mailto:{{support_email}}">{{support_email}}</a>. Our hours are {{support_hours}} ({{support_timezone}}).</p>
    """
]

LEGAL_NOTICE = [
    """
<h2>Legal Notice</h2>
<p>This website is operated by {{legal_business_name}}.</p>
<ul>
  <li><strong>Company Name:</strong> {{legal_business_name}}</li>
  <li><strong>Trading As:</strong> {{brand_name}}</li>
  <li><strong>Address:</strong> {{business_address}}, {{business_city}}, {{business_state}} {{business_zip}}, {{business_country}}</li>
  <li><strong>Email:</strong> <a href="mailto:{{support_email}}">{{support_email}}</a></li>
  <li><strong>Phone:</strong> {{phone}}</li>
  <li><strong>Website:</strong> {{domain}}</li>
</ul>
<p>All content on this website is the property of {{legal_business_name}}. Prices and product availability are subject to change without notice.</p>
    """,
    """
<h2>Corporate Information</h2>
<p>The platform available at {{domain}} is legally owned and managed by {{legal_business_name}}.</p>
<h3>Contact Details</h3>
<p><strong>Business Name:</strong> {{legal_business_name}} (doing business as {{brand_name}})<br>
<strong>Headquarters:</strong> {{business_address}}, {{business_city}}, {{business_state}} {{business_zip}}, {{business_country}}<br>
<strong>Customer Support Email:</strong> <a href="mailto:{{support_email}}">{{support_email}}</a><br>
<strong>Contact Number:</strong> {{phone}}</p>
<p>Any unauthorized reproduction of the materials found on this site is strictly prohibited by law.</p>
    """,
    """
<h2>Website Impressum</h2>
<p>The following legal information is provided in accordance with international ecommerce standards regarding the operation of {{domain}}.</p>
<p><strong>Operator:</strong> {{legal_business_name}}<br>
<strong>Brand:</strong> {{brand_name}}<br>
<strong>Location:</strong> {{business_address}}, {{business_city}}, {{business_state}} {{business_zip}}, {{business_country}}<br>
<strong>Telephone:</strong> {{phone}}<br>
<strong>Electronic Mail:</strong> <a href="mailto:{{support_email}}">{{support_email}}</a></p>
<p>The operator assumes responsibility for the content published on this domain. We strive to keep our catalog up-to-date and accurate.</p>
    """
]

PRIVACY = [
    """
<h2>Privacy Policy</h2>
<p>This Privacy Policy describes how {{brand_name}} ("we", "us", or "our") collects, uses, and discloses your Personal Information when you visit or make a purchase from {{domain}} (the "Site").</p>
<h3>Information We Collect</h3>
<p>When you visit the Site, we collect certain information about your device, your interaction with the Site, and information necessary to process your purchases. We may also collect additional information if you contact us for customer support.</p>
<h3>Sharing Personal Information</h3>
<p>We share your Personal Information with service providers to help us provide our services and fulfill our contracts with you. For example, we use Shopify to power our online store.</p>
<h3>Your Rights</h3>
<p>If you are a resident of certain regions, you have the right to access the Personal Information we hold about you and to ask that your Personal Information be corrected, updated, or erased.</p>
<h3>Contact Us</h3>
<p>For more information about our privacy practices, if you have questions, or if you would like to make a complaint, please contact us by email at <a href="mailto:{{support_email}}">{{support_email}}</a> or by mail using the details provided below:</p>
<p>{{legal_business_name}}<br>{{business_address}}, {{business_city}}, {{business_state}} {{business_zip}}, {{business_country}}</p>
    """,
    """
<h2>Data Protection & Privacy Policy</h2>
<p>At {{brand_name}}, we respect your privacy and are committed to protecting the personal data you share with us on {{domain}}.</p>
<h3>Collection of Data</h3>
<p>We collect device information (like your IP address, browser type, and time zone) automatically when you browse our store. When you make a purchase, we collect order information including your name, billing address, shipping address, and payment confirmation details.</p>
<h3>Use of Your Data</h3>
<p>Your order information is used strictly to fulfill your purchases, arrange for shipping, and provide you with invoices and order confirmations. We use device information to screen for potential risk and fraud, and to improve our website architecture.</p>
<h3>Third-Party Sharing</h3>
<p>We process your store data using the Shopify ecommerce platform. We may also share your Personal Information to comply with applicable laws and regulations, or to respond to lawful requests for information we receive.</p>
<h3>Contacting Us</h3>
<p>If you have any questions regarding your data, please write to us at <a href="mailto:{{support_email}}">{{support_email}}</a> or call {{phone}}.</p>
    """,
    """
<h2>Privacy Notice</h2>
<p>Welcome to the {{brand_name}} privacy notice. We value the trust you place in us when you provide us with your personal details at {{domain}}.</p>
<h3>1. What Information Do We Collect?</h3>
<p>We collect information that you voluntarily provide to us when registering, expressing an interest in our products, or contacting us. This includes contact data and purchase histories.</p>
<h3>2. How Do We Use Your Information?</h3>
<p>We process your information for purposes based on legitimate business interests, the fulfillment of our contract with you, compliance with our legal obligations, and your consent.</p>
<h3>3. Will Your Information Be Shared?</h3>
<p>We only share information with your consent, to comply with laws, to provide you with services, to protect your rights, or to fulfill business obligations. Shopify acts as our main data processor.</p>
<h3>4. How to Contact Us</h3>
<p>If you have questions or comments about this notice, you may email us at <a href="mailto:{{support_email}}">{{support_email}}</a> or by post to:<br>
{{legal_business_name}}<br>
{{business_address}}, {{business_city}}, {{business_state}} {{business_zip}}, {{business_country}}</p>
    """
]

PAYMENT = [
    """
<h2>Payment Policy</h2>
<p>At {{brand_name}}, we strive to make your checkout process as seamless and secure as possible.</p>
<h3>Accepted Payment Methods</h3>
<p>We accept the following forms of payment: <strong>{{payment_methods}}</strong>.</p>
<h3>Currency</h3>
<p>All prices listed on our store are in <strong>{{currency}}</strong>.</p>
<h3>Secure Checkout</h3>
<p>Our store is hosted on Shopify, which provides us with a secure, PCI-compliant online e-commerce platform. Your payment data is encrypted and handled securely.</p>
    """,
    """
<h2>Billing & Payments</h2>
<p>Review our accepted payment options before placing your order on {{domain}}.</p>
<ul>
<li><strong>Payment Gateways:</strong> We process all payments safely. You can pay using {{payment_methods}}.</li>
<li><strong>Store Currency:</strong> We operate strictly in {{currency}}. Conversion rates may apply if you are using an international card.</li>
<li><strong>Security:</strong> All sensitive billing information is encrypted during transmission using industry-standard SSL technology.</li>
</ul>
<p>If your card is declined, please verify your billing address or contact your bank.</p>
    """,
    """
<h2>How to Pay</h2>
<p>Thank you for choosing {{brand_name}}! We are committed to protecting your financial information.</p>
<h3>Methods of Payment</h3>
<p>During checkout, you will be prompted to select a payment method. We happily accept {{payment_methods}}. We do not store your raw credit card numbers on our servers; they are processed securely by our trusted payment partners.</p>
<h3>Pricing Currency</h3>
<p>Please note that all orders are finalized in {{currency}}.</p>
    """
]

SHIPPING = [
    """
<h2>Shipping Policy</h2>
<p>Thank you for shopping at {{brand_name}}. Following are the terms and conditions that constitute our Shipping Policy.</p>
<h3>Shipping Destinations</h3>
<p>We currently ship to <strong>{{shipping_regions}}</strong>.</p>
<h3>Order Processing Time</h3>
<p>All orders are processed within <strong>{{processing_time}}</strong>. Orders are not shipped or delivered on weekends or holidays.</p>
<h3>Transit and Delivery Time</h3>
<p>Standard transit time is <strong>{{transit_time}}</strong>. The estimated total delivery time from the moment you place your order is <strong>{{estimated_delivery_time}}</strong>.</p>
<h3>Shipping Rates</h3>
<p>Shipping charges for your order will be calculated and displayed at checkout. Our standard shipping cost is <strong>{{shipping_cost}}</strong>. Do we offer free shipping? <strong>{{free_shipping}}</strong>.</p>
<h3>Contact Us</h3>
<p>If you have any questions about the delivery of your order, please contact us at <a href="mailto:{{support_email}}">{{support_email}}</a>.</p>
    """,
    """
<h2>Delivery Information</h2>
<p>At {{brand_name}}, our goal is to offer you the best shipping options, no matter where you live.</p>
<h3>Where We Ship</h3>
<p>We distribute our products throughout {{shipping_regions}}.</p>
<h3>Shipping Costs</h3>
<p>Our standard flat-rate shipping is {{shipping_cost}}. Customers often ask if we have free shipping—the answer is {{free_shipping}}.</p>
<h3>Timelines</h3>
<ul>
<li><strong>Processing time:</strong> Order verification, quality check, and packaging takes {{processing_time}}.</li>
<li><strong>Shipping time:</strong> This refers to the time it takes for items to be shipped from our warehouse to the destination. It usually takes {{transit_time}}.</li>
<li><strong>Total delivery time:</strong> You can expect your package in {{estimated_delivery_time}}.</li>
</ul>
<p>For assistance, reach out to <a href="mailto:{{support_email}}">{{support_email}}</a>.</p>
    """,
    """
<h2>Shipping & Handling</h2>
<p>We know you are excited to receive your order from {{brand_name}}. Here is a detailed breakdown of our shipping procedures.</p>
<h3>Regions and Costs</h3>
<p>We are pleased to provide shipping to {{shipping_regions}}. The base cost for delivery is {{shipping_cost}}. We also provide free shipping: {{free_shipping}}.</p>
<h3>When Will I Get My Order?</h3>
<p>Our fulfillment team needs {{processing_time}} to prepare and dispatch your goods. Once in the hands of the carrier, the transit time is {{transit_time}}. Therefore, your total estimated delivery timeframe is {{estimated_delivery_time}}.</p>
<h3>Tracking</h3>
<p>You will receive a Shipment Confirmation email once your order has shipped containing your tracking number(s).</p>
    """
]

TERMS = [
    """
<h2>Terms of Service</h2>
<p>Welcome to {{brand_name}}. This website ({{domain}}) is operated by {{legal_business_name}}.</p>
<h3>1. General Conditions</h3>
<p>By visiting our site and/ or purchasing something from us, you engage in our "Service" and agree to be bound by the following terms and conditions.</p>
<h3>2. Products or Services</h3>
<p>Certain products or services may be available exclusively online through the website. These products or services may have limited quantities and are subject to return or exchange only according to our Refund Policy.</p>
<h3>3. Accuracy of Billing and Account Information</h3>
<p>We reserve the right to refuse any order you place with us. You agree to provide current, complete and accurate purchase and account information for all purchases made at our store.</p>
<h3>4. Governing Law</h3>
<p>These Terms of Service shall be governed by and construed in accordance with the laws applicable in {{business_country}}.</p>
<h3>5. Contact Information</h3>
<p>Questions about the Terms of Service should be sent to us at <a href="mailto:{{support_email}}">{{support_email}}</a>.</p>
    """,
    """
<h2>Terms and Conditions</h2>
<p>Please read these Terms carefully before accessing or using {{domain}}. By accessing or using any part of the site, you agree to be bound by these Terms.</p>
<h3>Online Store Terms</h3>
<p>By agreeing to these Terms, you represent that you are at least the age of majority in your state or province of residence. You may not use our products for any illegal or unauthorized purpose.</p>
<h3>Modifications to the Service and Prices</h3>
<p>Prices for our products are subject to change without notice. We reserve the right at any time to modify or discontinue the Service without notice at any time.</p>
<h3>Third-Party Links</h3>
<p>Certain content, products and services available via our Service may include materials from third-parties.</p>
<h3>Contact</h3>
<p>If you have any inquiries regarding these terms, contact {{legal_business_name}} at <a href="mailto:{{support_email}}">{{support_email}}</a>.</p>
    """,
    """
<h2>User Agreement</h2>
<p>This agreement outlines the rules and regulations for the use of {{brand_name}}'s Website, located at {{domain}}.</p>
<h3>License</h3>
<p>Unless otherwise stated, {{legal_business_name}} and/or its licensors own the intellectual property rights for all material on {{brand_name}}. All intellectual property rights are reserved.</p>
<h3>Purchases</h3>
<p>If you wish to purchase any product made available through the store, you may be asked to supply certain information relevant to your Purchase including, without limitation, your credit card number, the expiration date of your credit card, and your billing address.</p>
<h3>Governing Law</h3>
<p>Our failure to enforce any right or provision of these Terms will not be considered a waiver of those rights. These Terms are governed by the laws of {{business_country}}.</p>
    """
]

RETURNS = [
    """
<h2>Refund and Return Policy</h2>
<p>We want you to be completely satisfied with your purchase from {{brand_name}}. If you are not satisfied, you may return the item subject to our policy below.</p>
<h3>Return Window</h3>
<p>You have <strong>{{return_window}}</strong> from the date of delivery to initiate a return.</p>
<h3>Return Process</h3>
<p>To start a return, please contact us at <a href="mailto:{{support_email}}">{{support_email}}</a>. Returns must be sent <strong>{{return_method}}</strong>. The return shipping cost is: <strong>{{return_shipping_cost}}</strong>.</p>
<h3>Refunds</h3>
<p>Once your return is received and inspected, we will notify you of the approval or rejection of your refund. If approved, your refund will be processed and a credit will automatically be applied to your original method of payment within <strong>{{refund_processing_time}}</strong>.</p>
<h3>Damaged or Incorrect Items</h3>
<p>Please inspect your order upon reception and contact us immediately if the item is defective, damaged, or if you receive the wrong item, so that we can evaluate the issue and make it right.</p>
    """,
    """
<h2>Return Policy</h2>
<p>At {{brand_name}}, we stand behind the quality of our goods. If you are not happy with your order, please review our return guidelines.</p>
<ul>
<li><strong>Eligibility:</strong> You must request your return within {{return_window}} of receiving your items.</li>
<li><strong>Procedure:</strong> Reach out to us at <a href="mailto:{{support_email}}">{{support_email}}</a>. Send the items back {{return_method}}.</li>
<li><strong>Shipping Fees:</strong> For returns, the shipping costs are handled as follows: {{return_shipping_cost}}.</li>
<li><strong>Refund Timeline:</strong> After we receive and inspect the product, your refund will be issued to your bank or card within {{refund_processing_time}}.</li>
</ul>
<p>If you have received a faulty item, please include photographs in your email so we can expedite a replacement or refund.</p>
    """,
    """
<h2>Returns & Exchanges</h2>
<p>Our goal is to make your shopping experience at {{brand_name}} as risk-free as possible.</p>
<h3>How Many Days Do I Have?</h3>
<p>Our standard return window is {{return_window}}. If this timeframe has gone by since your package was delivered, we unfortunately cannot offer you a refund or exchange.</p>
<h3>How to Send Items Back</h3>
<p>All returned merchandise should be sent {{return_method}}. Please be aware that {{return_shipping_cost}}.</p>
<h3>Getting Your Money Back</h3>
<p>We will email you upon receiving your returned package. Once we verify the item's condition, we will trigger a refund. The funds should appear in your account in {{refund_processing_time}}.</p>
    """
]

CANCELLATION = [
    """
<h2>Order Cancellation Policy</h2>
<p>We understand that sometimes you may need to cancel an order after it has been placed on {{domain}}.</p>
<h3>Cancellation Timeframe</h3>
<p>You may cancel your order for a full refund within <strong>{{cancellation_window}}</strong> of placing the order.</p>
<h3>How to Cancel</h3>
<p>To request a cancellation, please email us immediately at <a href="mailto:{{support_email}}">{{support_email}}</a> with your order number. Once the cancellation window has passed or the order has been processed for shipping, we can no longer cancel the order.</p>
<p>If the order has already shipped, please refer to our Refund & Return Policy to initiate a return after the item arrives.</p>
    """,
    """
<h2>Cancellations</h2>
<p>At {{brand_name}}, we process orders quickly to ensure fast delivery. Therefore, we have a strict order cancellation window.</p>
<h3>Your Grace Period</h3>
<p>If you change your mind, you have exactly {{cancellation_window}} to cancel your order. Send an email to <a href="mailto:{{support_email}}">{{support_email}}</a> to request the cancellation.</p>
<h3>Late Cancellations</h3>
<p>If {{cancellation_window}} has elapsed, our warehouse has likely already prepared your box. At that stage, you must wait for delivery and request a standard return.</p>
    """,
    """
<h2>Cancelling an Order</h2>
<p>Mistakes happen! If you accidentally purchased the wrong item or changed your mind, here is how you can cancel your order.</p>
<ul>
<li><strong>Deadline:</strong> You must act within {{cancellation_window}}.</li>
<li><strong>Action:</strong> Email us at <a href="mailto:{{support_email}}">{{support_email}}</a> with the subject line "CANCELLATION" and your order number.</li>
<li><strong>Consequence:</strong> If you miss the {{cancellation_window}} deadline, the order is locked for shipping. You will have to return it manually once it arrives.</li>
</ul>
    """
]

WARRANTY = [
    """
<h2>Warranty Policy</h2>
<p>At {{brand_name}}, we stand behind the quality of our {{product_term}}.</p>
<h3>Warranty Coverage</h3>
<p>Is a warranty provided for our products? <strong>{{warranty_enabled}}</strong>.</p>
<p>If applicable, the warranty period is <strong>{{warranty_period}}</strong> from the date of purchase. This warranty covers manufacturing defects under normal use and does not cover damage caused by misuse, accidents, or unauthorized modifications.</p>
<h3>Making a Claim</h3>
<p>To make a warranty claim, please contact our support team at <a href="mailto:{{support_email}}">{{support_email}}</a> with your order details and photos of the defect.</p>
    """,
    """
<h2>Product Warranty</h2>
<p>We want you to feel confident shopping with {{brand_name}}.</p>
<ul>
<li><strong>Coverage status:</strong> {{warranty_enabled}}</li>
<li><strong>Duration:</strong> {{warranty_period}}</li>
</ul>
<p>Our warranty (when applicable) covers defects in materials and workmanship. It does not cover wear and tear, intentional damage, or modifications. Contact <a href="mailto:{{support_email}}">{{support_email}}</a> to initiate a claim.</p>
    """,
    """
<h2>Warranty Information</h2>
<p>If you experience issues with your {{product_term}}, you might be covered by our warranty policy.</p>
<h3>Policy Details</h3>
<p>Warranty availability: {{warranty_enabled}}.</p>
<p>The standard warranty duration spans {{warranty_period}}. We require proof of purchase and evidence of the defect to process any warranty replacement or repair. We reserve the right to deny claims for products that have been used outside of their intended {{customer_need}} purposes.</p>
    """
]

