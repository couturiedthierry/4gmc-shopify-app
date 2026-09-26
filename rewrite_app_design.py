import sys

content = open('static/app.js', encoding='utf8').read()

# Replace the UI template for Store Design
start_ui = "return header('Store design',"
end_ui = "</section>`+\n `<div class=\"grid two-col\">"
start_idx = content.find(start_ui)
end_idx = content.find(end_ui)

if start_idx != -1 and end_idx != -1:
    new_ui = '''return header('Store design','Choose store branding, colors, layout, and trigger complete Shopify store design generation.')+
`<section class="card full store-design-hero-card" style="margin-bottom:18px;">
 <h2>Generate & Build Store Design</h2>
 <p class="sub">Build responsive Liquid theme templates, map curated collections to dynamic carousels, setup 4-column footer, native payment SVG icons, checkout branding, Track123 tracking link, and SEO proposals.</p>
 <form id="store-design-form" class="form-grid">
  <div class="full actions">
   <button class="primary" ${!busy?'':'disabled'}>Generate & Build Store Design</button>
   <button type="button" class="secondary" data-action="publish-store-design" ${!busy?'':'disabled'}>Publish Verified Store Design</button>
  </div>
 </form>
 <p class="helper">${store.connected?'Ready to build & stage unpublished draft theme, navigation, payment icons & Track123 to Shopify.':'Ready to generate complete store design spec. Connect Shopify to publish to live store.'}</p>
'''
    content = content[:start_idx] + new_ui + content[end_idx:]

# Replace the event listener for store-design-form
old_event = "if(form.id==='store-design-form')perform(async()=>{const refUrl=val('store-design-reference');await api('/api/store-design/build','POST',{reference_url:refUrl});return 'Started store design generation. Follow progress in Task center or preview below.';});"
new_event = "if(form.id==='store-design-form')perform(async()=>{await api('/api/store-design/build','POST',{});return 'Started store design generation. Follow progress in Task center or preview below.';});"
content = content.replace(old_event, new_event)

open('static/app.js', 'w', encoding='utf8').write(content)
print("Updated static/app.js")
