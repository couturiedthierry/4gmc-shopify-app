const $ = (id) => document.getElementById(id);
let data = null, view = 'overview', editProduct = null, editPage = null, usaPlan = null, siteKitPlan = null, siteKitLastRun = null, siteKitJob = null, siteKitPollTimer = null, catalogJob = null, catalogPollTimer = null, productRun = null, previewTab = 'home', busy = false;
const names = {overview:'Overview',products:'Products',pages:'Pages & policies',design:'Store design',business:'Business & brand',connections:'Connections',tasks:'Task center',activity:'Activity'};
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const val = (id) => $(id)?.value.trim() || '';
const brandAssetUrl = (kind, metadata) => metadata?.digest?`/api/store/brand-assets/${kind}?v=${encodeURIComponent(metadata.digest)}`:'';
const readBrandFile = (file) => new Promise((resolve,reject)=>{
  const reader=new FileReader();
  reader.onerror=()=>reject(new Error('The selected image could not be read.'));
  reader.onload=()=>{
    const value=String(reader.result||''),comma=value.indexOf(',');
    if(comma<0)return reject(new Error('The selected image could not be read.'));
    resolve({filename:file.name,content_type:file.type||'application/octet-stream',data:value.slice(comma+1)});
  };
  reader.readAsDataURL(file);
});
const messageText = (value, fallback='The request could not be completed') => {
 if(typeof value==='string'&&value.trim())return value;
 if(Array.isArray(value))return value.map(item=>messageText(item,'')).filter(Boolean).join(' · ')||fallback;
 if(value&&typeof value==='object')return messageText(value.msg||value.message||value.detail,JSON.stringify(value));
 return fallback;
};
const hideToast = () => { const el=$('toast'); el.classList.remove('show','persistent'); };
const showToast = (message, persistent=false) => { const el=$('toast'); el.textContent=messageText(message,'Saved successfully'); el.classList.toggle('persistent',persistent); el.classList.add('show'); clearTimeout(showToast.timer); if(!persistent)showToast.timer=setTimeout(hideToast,7000); };
$('toast').addEventListener('click',hideToast);
async function api(path, method='GET', body) {
  let response;
  try{response=await fetch(path,{method,credentials:'same-origin',headers:{'content-type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});}
  catch{throw new Error('The connection to 4GMC was interrupted. Long tasks keep running on the server and their status will be restored automatically.');}
  const result=await response.json().catch(()=>({}));
  if(!response.ok) throw new Error(messageText(result.detail));
  return result;
}
async function refresh(){
  try{
   data=await api('/api/state');
   if(data.store.policy_source_url){try{siteKitPlan=await api('/api/site-kit/plan');}catch{siteKitPlan=null;}}
   if(data.site_kit_job)watchSiteKitJob(data.site_kit_job);
   const activeCatalog=(data.jobs||[]).find(job=>job.kind==='catalog'&&job.store_id===data.active_store_id&&['queued','running'].includes(job.status));
   if(activeCatalog)watchCatalogJob(activeCatalog);
   $('login').classList.add('hidden');$('app').classList.remove('hidden');render();
  }
  catch(error){if(error.message==='Sign in to continue'){$('login').classList.remove('hidden');$('app').classList.add('hidden');return;}throw error;}
}
const siteKitRunning = () => ['queued','running'].includes(siteKitJob?.status);
function watchSiteKitJob(job){
 siteKitJob=job;siteKitLastRun=job.progress||'Generating destination-brand pages…';clearTimeout(siteKitPollTimer);
 if(siteKitRunning())siteKitPollTimer=setTimeout(pollSiteKitJob,1800);
}
async function pollSiteKitJob(){
 if(!siteKitJob?.id)return;
 try{
  const job=await api('/api/jobs/'+siteKitJob.id);siteKitJob=job;siteKitLastRun=job.progress;
  if(view==='pages'&&data)render();
  if(siteKitRunning()){siteKitPollTimer=setTimeout(pollSiteKitJob,1800);return;}
  if(job.status==='failed'){siteKitJob=null;showToast(job.error||'Page generation failed.',true);await refresh();return;}
  siteKitJob=null;
  if(job.store_id!==data.active_store_id){await refresh();showToast(`Page generation finished for ${job.store_name}. Select that store to review or publish it.`);return;}
  siteKitPlan=await api('/api/site-kit/plan');
  const skipped=job.result?.skipped?.length?` Shopify-managed pages skipped: ${job.result.skipped.join(', ')}.`:'';
  if(data.store.connected){const result=await api('/api/site-kit/publish','POST',{fingerprint:siteKitPlan.fingerprint});siteKitPlan=await api('/api/site-kit/plan');siteKitLastRun=result.failed?`Generated the pages, but publishing stopped at ${result.failed}: ${result.detail}`:`Generated and published ${result.published.length} pages and policies in Shopify.`;}
  else siteKitLastRun=`Generated ${siteKitPlan.pages.length} destination-brand pages. Connect Shopify to publish them.`;
  await refresh();showToast(siteKitLastRun+skipped);
 }catch(error){showToast(error?.message||error,true);siteKitPollTimer=setTimeout(pollSiteKitJob,5000);}
}
async function startSiteKitJob(sourceUrl){
 if(siteKitRunning())return;
 busy=true;
 try{const job=await api('/api/site-kit/prepare-job','POST',{source_url:sourceUrl});watchSiteKitJob(job);render();showToast('Page generation started. You can leave this screen while it continues.');}
 catch(error){showToast(error?.message||error,true);}
 finally{busy=false;if(data)render();}
}
const wait = milliseconds => new Promise(resolve=>setTimeout(resolve,milliseconds));
async function waitForSiteKitGeneration(sourceUrl,onProgress){
 let job=await api('/api/site-kit/prepare-job','POST',{source_url:sourceUrl});
 while(['queued','running'].includes(job.status)){
  onProgress(job.progress+(job.total?` (${job.completed}/${job.total})`:''));
  await wait(1800);job=await api('/api/jobs/'+job.id);
 }
 if(job.status==='failed')throw new Error(job.error||'Page generation failed.');
 onProgress(job.progress);return job;
}
const catalogRunning = () => ['queued','running'].includes(catalogJob?.status);
function watchCatalogJob(job){
 catalogJob=job;productRun=job.progress||'Building and publishing the catalog…';clearTimeout(catalogPollTimer);
 if(catalogRunning())catalogPollTimer=setTimeout(pollCatalogJob,1800);
}
async function pollCatalogJob(){
 if(!catalogJob?.id)return;
 try{
  const job=await api('/api/jobs/'+catalogJob.id);catalogJob=job;productRun=job.progress;
  if(view==='products'&&data)render();
  if(catalogRunning()){catalogPollTimer=setTimeout(pollCatalogJob,1800);return;}
  catalogJob=null;await refresh();
  if(job.status==='failed'){showToast(job.error||'Catalog generation failed.',true);return;}
  const count=job.result?.published?.length||job.completed||0;
  productRun=`Published ${count} products with branded images, inventory, collections, and GMC identifiers.`;
  showToast(productRun);
 }catch(error){showToast(error?.message||error,true);catalogPollTimer=setTimeout(pollCatalogJob,5000);}
}
async function startCatalogJob(sourceUrl){
 if(catalogRunning())return;
 busy=true;
 try{const job=await api('/api/products/catalog-job','POST',{source_url:sourceUrl});watchCatalogJob(job);render();showToast('Catalog generation started. Follow every product from Task center.');}
 catch(error){showToast(error?.message||error,true);}
 finally{busy=false;if(data)render();}
}
async function waitForCatalogGeneration(sourceUrl,onProgress){
 let job=await api('/api/products/catalog-job','POST',{source_url:sourceUrl});
 while(['queued','running'].includes(job.status)){
  onProgress(job.progress+(job.total?` (${job.completed}/${job.total})`:''));
  await wait(1800);job=await api('/api/jobs/'+job.id);
 }
 if(job.status==='failed')throw new Error(job.error||'Catalog generation failed.');
 onProgress(job.progress);return job;
}
function header(title, subtitle, actions='') {return `<div class="page-head"><div><p class="eyebrow">4GMC / MERCHANT WORKSPACE</p><h1>${esc(title)}</h1><p>${esc(subtitle)}</p></div><div class="actions">${actions}</div></div>`}
function metric(label,value,sub){return `<div class="metric"><small>${esc(label)}</small><strong>${esc(value)}</strong><span>${esc(sub)}</span></div>`}
function finding(item){return `<div class="finding"><div class="finding-icon">!</div><div class="finding-main"><strong>${esc(item.label)}</strong><p>${esc(item.detail)}</p></div><span class="tag">${esc(item.area)}</span></div>`}
function overview(){
 const f=data.findings, store=data.store;
 return header(`Good day. Let's get your store ready.`, `A clear view of ${store.name || 'your store'} and what needs attention.`, `<button class="secondary" data-view="business">Update store details</button>`) +
 `<div class="grid metrics">${metric('Readiness issues',f.length,'From local checks')}${metric('Products',data.products.length,'Saved in this workspace')}${metric('Pages',data.pages.length,'Saved in this workspace')}${metric('Shopify',store.connected?'Connected':'Not connected','Store connection')}</div>`+
 `<div class="grid two-col"><section class="card"><h2>What needs attention</h2><p class="sub">These are local checks. Google account issues appear after GMC is connected.</p>${f.length?f.slice(0,7).map(finding).join(''):'<div class="empty">No local issues found in this workspace.</div>'}${f.length>7?`<p class="helper">${f.length-7} more items to address.</p>`:''}</section><section class="card"><h2>Setup progress</h2><p class="sub">Complete the essentials before publishing.</p>${check('Business profile',Boolean(store.business.business_name&&store.business.email),'Add your real business and contact information')}${check('Shopify store',store.connected,'Connect the destination store')}${check('Claude Fable 5',data.ai_connected,'Ready for copy and policy drafts')}${check('Products',data.products.length>0,'Import or create your first product')}${check('Store pages',data.pages.length>0,'Prepare standard pages from your source store')}<div class="section-line"></div><div class="actions"><button class="primary" data-view="products">Prepare products</button><button class="secondary" data-view="pages">Prepare pages</button></div></section></div>`;
}
function check(name,done,sub){return `<div class="checkrow"><span class="check-icon ${done?'':'off'}">${done?'✓':'·'}</span><div><strong>${esc(name)}</strong><small>${esc(sub)}</small></div></div>`}
function products(){
 const source=data.store.product_source_url||'';
 const result=productRun?`<div class="note">${esc(productRun)}${catalogRunning()&&catalogJob.total?` (${catalogJob.completed}/${catalogJob.total})`:''}</div>`:'';
 const list=data.products.length?data.products.map(product=>{
  const g=product.gmc_data||{}, roles=(product.ai_image_manifest||[]).map(item=>item.role);
  const identifier=g.gtin?`GTIN verified`:(g.mpn?`Private-label MPN`:`Identifier needs attention`);
  const inventory=product.inventory_tracked?`${product.inventory_quantity??0} tracked`:(g.availability==='in_stock'?'Available · quantity untracked':'Out of stock');
  return `<div class="item product-automation-item"><div><strong>${esc(product.title)}</strong><small>${esc(product.source_title)} · ${esc(product.price?product.price+' '+(data.store.business.currency||'USD'):'Price unavailable')} · ${esc(product.status)}</small><small>${esc(product.collection_title||'Featured Products')} · ${esc(identifier)} · ${esc(inventory)}</small><small>Images: ${esc(roles.length?roles.join(', '):'pending hero, detail, lifestyle')}</small></div>${product.status==='published'?'<span class="tag good">Online Store</span>':''}</div>`;
 }).join(''):'<div class="empty">No products imported yet.</div>';
 return header('Products','Build a curated private-label catalog with consistent branded photography, collections, inventory, and Google Merchant product identification.')+
 `<div class="grid two-col"><div class="grid"><section class="card"><h2>Product source website</h2><p class="sub">4GMC scans the public Shopify catalog, selects up to 20 strong physical products across up to four coherent categories, and keeps one available representative variation per product.</p><form id="product-source-form" class="form-grid"><label class="full">Source website homepage<input id="product-source-url" type="url" value="${esc(source)}" placeholder="https://product-source-store.com" required></label><div class="full actions"><button class="primary" ${data.store.connected&&!busy&&!catalogRunning()?'':'disabled'}>${catalogRunning()?'Catalog running…':'Build & publish catalog'}</button><button type="button" class="secondary" data-view="tasks">Task center</button></div></form><p id="catalog-progress" class="helper">${data.store.connected?'Source and destination currencies must match. Products publish automatically after every validation passes.':'Connect your Shopify store before publishing products.'}</p>${result}</section><section class="card"><h2>Automated catalog</h2><p class="sub">${data.products.length} products · ${(data.collections||[]).length} Shopify collections</p><div class="list">${list}</div></section></div><div class="grid"><section class="card"><h2>Automatic product rules</h2>${check('Store connected',data.store.connected,'Required for immediate publication')}${check('Store logo',Boolean(data.store.brand.logo?.digest),'Required in the corner and on realistic product surfaces')}${check('Three-image gallery',data.image_connected,'Every hero, detail, and lifestyle image receives the exact corner logo')}${check('Product fidelity',true,'Construction, materials, controls, colors, and included parts are preserved')}${check('Catalog curation',true,'Maximum 20 physical products in four collections')}${check('Inventory',true,'Exact public quantities are tracked; unknown quantities remain untracked')}${check('GMC identification',true,'GTINs are checksum-tested and never invented; private-label MPNs are stable')}${check('Source facts',true,'Unsupported claims, certifications, and accessories are blocked')}<div class="note">The exact uploaded logo is composited into the top-left corner of every generated image. Gemini may also place it on up to three physically realistic product surfaces. Source barcodes from a different brand are kept only as supplier-confirmation candidates. 4GMC does not submit them as your private-label GTIN.</div></section></div></div>`;
}
function pages(){
 const source=data.store.policy_source_url||'';
 const managed=siteKitPlan?.pages||[];
 const list=managed.length?managed.map(page=>`<details class="site-kit-document"><summary><strong>${esc(page.title)}</strong><span class="tag ${page.status==='published'?'good':''}">${esc(page.status)}</span></summary><div class="site-kit-copy">${esc(page.body)}</div></details>`).join(''):
  source?'<p class="sub">The reference is saved. Generate the destination-brand pages again before publishing.</p>':'<div class="empty">Enter a reference store to generate original pages for your brand.</div>';
 const result=siteKitLastRun?`<div class="note">${esc(siteKitLastRun)}${siteKitRunning()&&siteKitJob.total?` (${siteKitJob.completed}/${siteKitJob.total})`:''}</div>`:'';
 const generating=siteKitRunning();
 return header('Pages & policies','Generate original pages for the selected brand. The reference store supplies structure and operating rules only; its text and identity are blocked from publication.')+
 `<div class="grid two-col"><div class="grid"><section class="card"><h2>Reference structure</h2><p class="sub">Enter the store containing your usual page structure and policy rules. 4GMC extracts a neutral outline, then writes new pages using only this destination store identity.</p><form id="policy-source-form" class="form-grid"><label class="full">Reference store homepage<input id="source-store-url" type="url" value="${esc(source)}" placeholder="https://your-reference-store.com" required></label><div class="full actions"><button class="primary" ${busy||generating?'disabled':''}>${generating?'Generating pages…':data.store.connected?'Generate brand pages & publish':'Generate brand pages'}</button></div></form><p class="helper">Reference sentences are never sent to the final writing step. Publication stops if source wording, branding, contacts, domains, placeholders, or missing destination facts are detected.</p></section><section class="card"><h2>Generated brand pages & policies</h2><p class="sub">${managed.length?`${managed.length} original documents generated for ${esc(data.store.business.business_name||data.store.name)}`:'About, Contact, FAQ, Shipping, Returns, Privacy, Terms, and referenced custom page types will appear here.'}</p>${result}${list}${source&&data.store.connected?'<div class="actions" style="margin-top:16px"><button class="secondary" data-action="run-site-kit">Publish verified brand pages</button></div>':''}</section></div><div class="grid"><section class="card"><h2>Destination identity</h2><p class="sub">Every generated page is sealed against these selected-store facts before Shopify publication.</p>${check('Store name',Boolean(data.store.business.business_name),'Required throughout generated pages')}${check('Domain',Boolean(data.store.business.domain_name),'Only your customer-facing domain is allowed')}${check('Contact email',Boolean(data.store.business.email),'Other email addresses are blocked')}${check('Store address',Boolean(data.store.business.address),'Used only where customer identity requires it')}${check('Phone',Boolean(data.store.business.phone),'Required on the Contact page')}${check('Country & currency',Boolean(data.store.business.country&&data.store.business.currency),'Used for destination policy context')}${check('Shopify',data.store.connected,'Destination for automatic publication')}<div class="actions"><button class="secondary" data-view="business">Edit store details</button></div></section><section class="card"><h2>Automatic brand guard</h2><p class="sub">Publishing fails closed when any of these checks does not pass.</p>${check('Neutral reference outline',true,'Source prose is removed before writing')}${check('Original destination wording',true,'Long source passages are rejected')}${check('Source identity scan',true,'Brands, emails, domains, and contacts are blocked')}${check('Required policy facts',true,'Shipping and return terms must be clear')}${check('Sealed content',true,'Later edits require regeneration and a new safety check')}</section></div></div>`;
}

function storefrontPreview(snapshot){
 const brand=snapshot.brand;
 const tabs=[{key:'home',title:'Home'},{key:'products',title:'Products'},...snapshot.pages.map(page=>({key:'page-'+page.id,title:page.title}))];
 const selected=tabs.some(tab=>tab.key===previewTab)?previewTab:'home';
 const nav=tabs.map(tab=>`<button type="button" data-preview-tab="${esc(tab.key)}" class="${selected===tab.key?'active':''}">${esc(tab.title)}</button>`).join('');
 const contact=snapshot.business;
 const logoUrl=brandAssetUrl('logo',brand.logo);
 const faviconUrl=brandAssetUrl('favicon',brand.favicon);
 const brandTitle=logoUrl?`<img class="preview-store-logo" src="${esc(logoUrl)}" alt="${esc(snapshot.name)} logo">`:`<b>${esc(snapshot.name)}</b>`;
 const domainTitle=`<span class="preview-domain">${faviconUrl?`<img src="${esc(faviconUrl)}" alt="">`:''}${esc(snapshot.domain)}</span>`;
 const contactDetails=`<div class="preview-contact"><strong>${esc(snapshot.name)}</strong><span>${esc(contact.email)} · ${esc(contact.phone)}</span><span>${esc(contact.address)}</span><span>Live Chat: Available on the website during business hours</span><span>Business Hours: Mon-Fri: 9:00 AM - 5:00 PM (Eastern Time)</span></div>`;
 const products=`<div class="preview-products">${snapshot.products.map(product=>`<article class="preview-product"><img src="${esc(product.image_url)}" alt="${esc(product.title)}"><strong>${esc(product.title)}</strong><span>${esc(product.price)} ${esc(contact.currency)}</span></article>`).join('')}</div>`;
 let content='';
 if(selected==='home')content=`<div class="preview-hero"><h2>${esc(snapshot.headline)}</h2><p>${esc(snapshot.intro)}</p><button type="button" class="primary" data-preview-tab="products">Shop products</button></div><div class="preview-section"><h3>Featured products</h3>${products}</div>`;
 else if(selected==='products')content=`<div class="preview-section"><h2>Products</h2>${products}</div>`;
 else {const page=snapshot.pages.find(item=>'page-'+item.id===selected);content=`<div class="preview-section"><h2>${esc(page?.title||'Page')}</h2><div class="preview-page-copy">${esc(page?.body||'')}</div>${page?.kind==='contact'?contactDetails:''}</div>`;}
 return `<div class="preview generated" style="--store-primary:${esc(brand.color)};--store-accent:${esc(brand.accent)}"><div class="preview-top">Free shipping in the United States</div><div class="preview-header"><div class="preview-store-brand">${brandTitle}</div>${domainTitle}</div><nav class="preview-nav" aria-label="Generated store pages">${nav}</nav>${content}<div class="preview-footer">${esc(snapshot.name)} · Contact: ${esc(contact.email)} · ${esc(contact.phone)}</div></div>`;
}
function design(){
 const store=data.store, brand=store.brand;
 const color=/^#[0-9a-fA-F]{6}$/.test(brand.color||'')?brand.color:'#2251dc';
 const accent=/^#[0-9a-fA-F]{6}$/.test(brand.accent||'')?brand.accent:'#6f9cff';
 const logoUrl=brandAssetUrl('logo',brand.logo),faviconUrl=brandAssetUrl('favicon',brand.favicon);
 const logoPreview=logoUrl?`<img class="brand-asset-image logo-image" src="${esc(logoUrl)}" alt="Current store logo">`:'<span class="asset-empty">No logo uploaded</span>';
 const faviconPreview=faviconUrl?`<img class="brand-asset-image favicon-image" src="${esc(faviconUrl)}" alt="Current store favicon">`:'<span class="asset-empty">No favicon uploaded</span>';
 const ready=Boolean(data.storefront);
 const preview=ready?storefrontPreview(data.storefront):'<div class="preview-blank" aria-label="Storefront preview is blank until the full store is generated"></div>';
 return header('Store design','Choose the store colors and upload its logo and favicon, then generate the complete store before previewing it.')+
 `<div class="grid two-col"><section class="card"><h2>Storefront preview</h2><p class="sub">${ready?'Generated from your saved branding, published pages, Contact details, and products.':'The preview stays blank until the complete store has been generated.'}</p>${preview}</section><div class="grid">
 <section class="card"><h2>Brand colors</h2><p class="sub">These colors are used for the generated preview and Gemini product mockups.</p><form id="design-colors-form" class="form-grid"><label>Primary color<input id="design-primary" type="color" value="${esc(color)}" required></label><label>Accent color<input id="design-accent" type="color" value="${esc(accent)}" required></label><div class="full actions"><button class="primary">Save colors</button></div></form><p class="helper">Changing colors clears the old preview until you regenerate the store and its product images.</p></section>
 <section class="card"><h2>Logo & favicon</h2><p class="sub">Upload the branding for this selected store. Replacing either file clears the preview until you regenerate it.</p><form id="brand-assets-form" class="form-grid brand-assets-form"><label class="full asset-upload-row"><span class="asset-preview" data-brand-preview="logo">${logoPreview}</span><span class="asset-upload-copy"><strong>Store logo</strong><small>PNG, JPG, or WebP · maximum 2 MB</small><input id="design-logo" type="file" accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"></span></label><label class="full asset-upload-row"><span class="asset-preview favicon-preview" data-brand-preview="favicon">${faviconPreview}</span><span class="asset-upload-copy"><strong>Favicon</strong><small>PNG, JPG, WebP, or ICO · maximum 512 KB</small><input id="design-favicon" type="file" accept=".png,.jpg,.jpeg,.webp,.ico,image/png,image/jpeg,image/webp,image/x-icon"></span></label><div class="full actions"><button class="primary">Upload branding</button></div></form></section>
 <section class="card"><h2>Generate complete store</h2><p class="sub">Use your saved business details to create and publish the source pages, Contact page, policies, products, and images. The preview appears only after all steps finish.</p><form id="storefront-build-form" class="form-grid"><label class="full">Reference store for page structure and policy rules<input id="build-page-source" type="url" value="${esc(store.policy_source_url||'')}" placeholder="https://pages-source-store.com" required></label><label class="full">Website to copy products from<input id="build-product-source" type="url" value="${esc(store.product_source_url||'')}" placeholder="https://products-source-store.com" required></label><div class="full actions"><button class="primary" ${store.connected&&!busy?'':'disabled'}>Generate full store</button></div></form><p id="storefront-progress" class="helper">${store.connected?'Ready to generate from the two source websites.':'Connect Shopify before generating and publishing the full store.'}</p><div class="section-line"></div><p class="helper">Shopify theme-file publishing requires separate theme access from Shopify. This screen previews the generated content and branding; it does not change the live theme.</p></section></div></div>`;
}

function business(){
 const s=data.store,b=s.business;
 const chat='Available on the website during business hours';
 const hours='Mon-Fri: 9:00 AM - 5:00 PM (Eastern Time)';
 return header('Business & brand','Use your real destination-store details. These values personalize the copied pages, policies and products.')+
 `<section class="card"><form id="store-form"><div class="form-grid"><label>Store name<input id="s-name" value="${esc(s.name)}" required></label><label>Domain name<input id="b-domain-name" value="${esc(b.domain_name||'')}" placeholder="yourstore.com" required></label><label>Contact email<input id="b-email" type="email" value="${esc(b.email||'')}" required></label><label>Store address<input id="b-address" value="${esc(b.address||'')}" required></label><label>Target country<input id="b-country" value="${esc(b.country||'United States')}" required></label><label>Currency<input id="b-currency" value="${esc(b.currency||'USD')}" maxlength="3" required></label><label>Phone<input id="b-phone" type="tel" value="${esc(b.phone||'')}" required></label><div class="full note"><strong>Live Chat:</strong> ${esc(chat)}<br><strong>Business Hours:</strong> ${esc(hours)}</div><div class="full actions"><button class="primary">Save store details</button></div></div></form></section>`;
}
function connections(){
 const s=data.store;
 const stores=data.stores||[];
 const active=data.active_store_id||1;
 const storeCards=stores.map(store=>`<section class="card store-card ${store.id===active?'store-card-active':''}">
  <div class="store-card-head"><div><h2>${esc(store.name||store.domain||'New store')}</h2><p class="sub">${esc(store.domain||'Add a Shopify address')}</p></div><span class="pill ${store.connected?'connected':''}">${store.connected?'Connected':store.id===active?'Selected':'Not connected'}</span></div>
  <form class="form-grid store-connection-form" data-id="${store.id}">
   <label class="full">Shopify admin address<input name="domain" value="${esc(store.domain||'')}" placeholder="your-store.myshopify.com" required></label>
   <div class="full actions"><button class="secondary">Save details</button>${store.id===active?'':`<button type="button" class="secondary" data-action="select-store" data-id="${store.id}">Use this store</button>`}</div>
  </form>
  ${store.id===active?`<div class="actions store-actions"><button class="primary" data-action="connect-shopify" ${data.shopify_ready&&store.domain?'':'disabled'}>${store.connected?'Reconnect Shopify':'Connect Shopify'}</button><button class="secondary" data-action="review-usa" ${store.connected?'':'disabled'}>Review USA setup</button></div>`:''}
 </section>`).join('');
 const addCard=`<section class="card add-store-card"><h2>+ Add one more store</h2><p class="sub">Add another store address. The same secure 4GMC Shopify application authorizes every store.</p><form id="add-store-form" class="form-grid">
  <label class="full">Shopify admin address<input name="domain" placeholder="another-store.myshopify.com" required></label>
  <div class="full actions"><button class="primary">Add store</button></div>
 </form></section>`;
 const plan=usaPlan?`<section class="card full"><h2>USA setup review</h2><p class="helper">Current Shopify name: ${esc(usaPlan.shop.name)} · Customer email: ${esc(usaPlan.shop.contactEmail)}</p><p class="sub">Shopify reports ${esc(usaPlan.shipping_system==='markets'?'market-based':'delivery-profile')} shipping. Applying this plan will pause ${usaPlan.markets_to_pause.length} other active region market(s) and replace ${usaPlan.shipping_to_replace} existing shipping zone(s) or option(s).</p>${check('Target market',true,'United States only · USD')}${check('Shipping',true,'Free at checkout · USD 0.00')}${usaPlan.manual_steps.length?`<div class="note"><strong>Shopify settings that require the store owner:</strong><br>${usaPlan.manual_steps.map(esc).join('<br>')}</div>`:''}<div class="actions"><button class="primary" data-action="apply-usa">Apply USA market & free shipping</button><button class="secondary" data-action="review-usa">Refresh review</button></div></section>`:'';
 return header('Connections','Select a store address, then authorize the shared 4GMC Shopify app to publish there.')+
 `<div class="note"><strong>One Shopify app for every store.</strong><br>The Client ID and Client Secret are stored once in Render. Each store receives its own encrypted access token after you click Connect Shopify.</div>`+
 `<div class="store-cards">${storeCards}${addCard}</div>
 <div class="grid two-col connection-extras">
 <section class="card"><h2>Claude Fable 5</h2><p class="sub">Used to prepare product copy and page drafts.</p><span class="pill ${data.ai_connected?'connected':''}">${data.ai_connected?'Configured':'Not configured'}</span><p class="helper">SmartAPI · Anthropic-compatible API · claude-fable-5</p><div class="section-line"></div><h2>Image generation</h2><p class="sub">Gemini 3.1 Flash Image creates branded product mockups.</p><span class="pill ${data.image_connected?'connected':''}">${data.image_connected?'Configured':'Not configured'}</span></section>
 <section class="card"><h2>Publishing for selected store</h2>${check('Shopify authorization',s.connected,'Connect '+(s.domain||'the destination store'))}${check('Pages, policies and products',s.connected,'Changes publish only to the selected store')}<p class="helper">Shopify authorization requires a public HTTPS app URL and the callback URL registered with your Shopify app.</p></section>
 ${plan}</div>`;
}
function tasks(){
 const jobs=data.jobs||[],active=jobs.filter(job=>['queued','running'].includes(job.status));
 const cards=jobs.length?jobs.map(job=>{const complete=job.status==='completed',failed=job.status==='failed';const percent=complete?100:job.total?Math.min(100,Math.round(job.completed/job.total*100)):job.status==='running'?8:0;const label=job.kind==='site_kit'?'Brand pages & policies':job.kind==='catalog'?'Products, images & publishing':job.kind;return `<article class="card task-card"><div class="task-head"><div><h2>${esc(label)}</h2><p class="sub">${esc(job.store_name)}${job.store_domain?' · '+esc(job.store_domain):''}</p></div><span class="pill ${complete?'connected':failed?'failed':''}">${esc(job.status)}</span></div><strong class="task-progress-label">${esc(job.progress)}</strong><div class="task-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${percent}"><span style="width:${percent}%"></span></div><small>${job.total?`${job.completed} of ${job.total} · `:''}${percent}%</small>${job.error?`<div class="task-error">${esc(job.error)}</div>`:''}${job.store_id!==data.active_store_id?`<div class="actions"><button class="secondary" data-action="select-store" data-id="${job.store_id}">Open this store</button></div>`:''}</article>`}).join(''):'<div class="empty">No background tasks yet. Start page or product generation from any store to see its progress here.</div>';
 return header('Task center','Run work for several stores at the same time and follow every task independently.')+`<div class="grid metrics task-metrics">${metric('Active tasks',active.length,'Running or waiting')}${metric('Parallel capacity',data.task_capacity||4,'Maximum simultaneous jobs')}${metric('Completed',jobs.filter(job=>job.status==='completed').length,'Recent background jobs')}${metric('Failed',jobs.filter(job=>job.status==='failed').length,'Errors remain visible')}</div><section class="card task-settings"><h2>Parallel processing</h2><p class="sub">Choose how many store jobs 4GMC may run at once. Page and catalog jobs are isolated per store, and every job keeps its own progress.</p><form id="task-settings-form" class="actions"><label>Simultaneous jobs<select id="task-capacity">${[1,2,4,6,8].map(value=>`<option value="${value}" ${value===(data.task_capacity||4)?'selected':''}>${value}</option>`).join('')}</select></label><button class="primary">Save capacity</button></form></section><div class="task-list">${cards}</div>`;
}
function activity(){return header('Activity','A record of preparation and store changes.')+`<section class="card"><h2>Recent activity</h2>${data.events.length?data.events.map(e=>`<div class="finding"><div class="finding-icon activity-icon">↗</div><div class="finding-main"><strong>${esc(e.message)}</strong><p>${esc(e.created_at)}</p></div></div>`).join(''):'<div class="empty">No activity yet.</div>'}</section>`}
function render(){
 $('store-domain').textContent=data.store.domain||'No store connected';$('crumb').textContent=names[view];
 document.querySelectorAll('#nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));
 $('main').innerHTML=({overview,products,pages,design,business,connections,tasks,activity}[view])();
}
async function perform(fn){if(busy)return;busy=true;try{const message=await fn();await refresh();showToast(typeof message==='string'?message:'Saved successfully');}catch(error){showToast(error?.message||error,true);}finally{busy=false;}}
$('login-form').addEventListener('submit',async e=>{e.preventDefault();try{await api('/api/login','POST',{password:val('password')});$('password').value='';$('login-error').textContent='';await refresh();}catch(error){$('login-error').textContent=error.message;}});
for(const id of ['logout','mobile-logout']) $(id).addEventListener('click',async()=>{
 try{await api('/api/logout','POST');data=null;await refresh();}
 catch(error){showToast(error?.message||error);}
});
document.body.addEventListener('click',e=>{
 const nav=e.target.closest('[data-view]');if(nav){view=nav.dataset.view;editPage=editProduct=null;render();return;}
 const previewButton=e.target.closest('[data-preview-tab]');if(previewButton){previewTab=previewButton.dataset.previewTab;render();return;}
 const button=e.target.closest('[data-action]');if(!button)return;
 const id=Number(button.dataset.id);
 switch(button.dataset.action){
  case 'edit-product':editProduct=id;render();break;
  case 'review-product':perform(async()=>{await api(`/api/products/${id}/review`,'POST');return 'Product reviewed and ready for Shopify draft upload.';});break;
  case 'upload-product':if(window.confirm('Send this reviewed product to Shopify as a hidden draft?'))perform(async()=>{await api(`/api/products/${id}/upload`,'POST');return 'Shopify draft uploaded and checked. Images may still be processing.';});break;
  case 'close-product':editProduct=null;render();break;
  case 'run-site-kit':perform(async()=>{siteKitPlan=await api('/api/site-kit/plan');const result=await api('/api/site-kit/publish','POST',{fingerprint:siteKitPlan.fingerprint});siteKitPlan=await api('/api/site-kit/plan');siteKitLastRun=result.failed?`Published ${result.published.length} documents; stopped at ${result.failed}: ${result.detail}`:`Published ${result.published.length} pages and policies in Shopify.`;return siteKitLastRun;});break;
  case 'edit-page':editPage=id;render();break;
  case 'close-page':editPage=null;render();break;
  case 'prepare-product':perform(async()=>{await api(`/api/products/${id}/prepare`,'POST');return 'Claude prepared a draft. Review it before use.';});break;
  case 'prepare-page':perform(async()=>{await api(`/api/pages/${id}/prepare`,'POST');return 'Claude prepared a page draft. Review it before use.';});break;
  case 'review-page':perform(async()=>{await api(`/api/pages/${id}/review`,'POST');return 'Reviewed. This exact draft is ready to publish.';});break;
  case 'publish-page':if(window.confirm('Publish this reviewed content to Shopify? Existing store policy text of the same type will be replaced.'))perform(async()=>{const result=await api(`/api/pages/${id}/publish`,'POST');return result.url?'Published and verified in Shopify.':'Published and verified.';});break;
  case 'select-store':perform(async()=>{await api('/api/stores/'+id+'/select','POST');usaPlan=null;siteKitPlan=null;siteKitLastRun='';editPage=editProduct=null;return 'Store selected.';});break;
  case 'connect-shopify':window.location.href='/api/shopify/connect';break;
  case 'review-usa':perform(async()=>{usaPlan=await api('/api/shopify/usa-plan');return 'USA setup review is ready.';});break;
  case 'apply-usa':if(usaPlan&&window.confirm('Apply USA-only region markets and replace merchant shipping settings with free USA shipping? This may pause other markets and remove their current shipping rates.'))perform(async()=>{const result=await api('/api/shopify/usa-apply','POST',{fingerprint:usaPlan.fingerprint});usaPlan=null;return result.manual_steps.length?'USA market and merchant shipping verified. Check the remaining Shopify store details.':'USA market and merchant shipping verified in Shopify.';});break;
 }
});
document.body.addEventListener('change',e=>{
 const input=e.target.closest('#design-logo,#design-favicon');
 if(!input||!input.files?.[0])return;
 const kind=input.id==='design-logo'?'logo':'favicon';
 const target=document.querySelector(`[data-brand-preview="${kind}"]`);
 if(!target)return;
 const url=URL.createObjectURL(input.files[0]);
 target.innerHTML=`<img class="brand-asset-image ${kind==='logo'?'logo-image':'favicon-image'}" src="${esc(url)}" alt="Selected ${kind} preview">`;
 setTimeout(()=>URL.revokeObjectURL(url),10000);
});
document.body.addEventListener('submit',e=>{
 const form=e.target;if(form.id==='login-form')return;if(!form.id&&!form.classList.contains('store-connection-form'))return;e.preventDefault();
 if(form.id==='design-colors-form')perform(async()=>{await api('/api/store','PUT',{name:data.store.name,domain:data.store.domain,business:data.store.business,brand:{color:val('design-primary'),accent:val('design-accent')}});return 'Brand colors saved.';});
 if(form.id==='brand-assets-form')perform(async()=>{
  const logo=$('design-logo').files[0],favicon=$('design-favicon').files[0];
  if(!logo&&!favicon)throw new Error('Choose a logo or favicon to upload.');
  if(logo){if(logo.size>2*1024*1024)throw new Error('Logo must be smaller than 2 MB.');await api('/api/store/brand-asset','PUT',{kind:'logo',...await readBrandFile(logo)});}
  if(favicon){if(favicon.size>512*1024)throw new Error('Favicon must be smaller than 512 KB.');await api('/api/store/brand-asset','PUT',{kind:'favicon',...await readBrandFile(favicon)});}
  return logo&&favicon?'Logo and favicon uploaded. Regenerate the store preview.':`${logo?'Logo':'Favicon'} uploaded. Regenerate the store preview.`;
 });
 if(form.id==='storefront-build-form')perform(async()=>{
  const pageSource=val('build-page-source'),productSource=val('build-product-source');
  await api('/api/storefront/reset','POST');
  data.storefront=null;render();
  const progress=$('storefront-progress');
  const stage=message=>{if(progress)progress.textContent=message;};
  try{
   if(!siteKitPlan||pageSource!==data.store.policy_source_url||siteKitPlan.pages.some(page=>page.status!=='published')){
    stage('Starting background generation for pages, policies, and Contact page…');
    await waitForSiteKitGeneration(pageSource,stage);
    siteKitPlan=await api('/api/site-kit/plan');
    stage('Publishing pages and policies to Shopify…');
    const pagesResult=await api('/api/site-kit/publish','POST',{fingerprint:siteKitPlan.fingerprint});
    if(pagesResult.failed)throw new Error('Page '+pagesResult.failed+': '+pagesResult.detail);
    siteKitPlan=await api('/api/site-kit/plan');
   }
   stage('Scanning and curating up to 20 products across four collections…');
   await waitForCatalogGeneration(productSource,stage);
   stage('Generating the complete storefront preview…');
   const result=await api('/api/storefront/generate','POST');
   previewTab='home';
   return 'Generated the store preview from '+result.pages+' pages and '+result.products+' products.';
  }catch(error){stage('Stopped: '+error.message);throw error;}
 });
 if(form.id==='store-form')perform(async()=>{usaPlan=null;siteKitPlan=null;await api('/api/store','PUT',{name:val('s-name'),domain:data.store.domain,business:{...data.store.business,business_name:val('s-name'),domain_name:val('b-domain-name'),email:val('b-email'),address:val('b-address'),country:val('b-country'),currency:val('b-currency'),phone:val('b-phone')},brand:data.store.brand});return 'Store details saved.';});
 if(form.id==='add-store-form')perform(async()=>{const fields=new FormData(form);await api('/api/stores','POST',{domain:fields.get('domain')});usaPlan=null;siteKitPlan=null;siteKitLastRun='';editPage=editProduct=null;return 'Store added and selected.';});
 if(form.id==='task-settings-form')perform(async()=>{const result=await api('/api/settings/task-capacity','PUT',{value:Number(val('task-capacity'))});data.task_capacity=result.value;return `Parallel task capacity set to ${result.value}.`;});
 if(form.classList.contains('store-connection-form'))perform(async()=>{const fields=new FormData(form);await api('/api/stores/'+form.dataset.id+'/connection','PUT',{domain:fields.get('domain')});usaPlan=null;return 'Shopify address saved. Authorize or reconnect to publish.';});
 if(form.id==='product-source-form')startCatalogJob(val('product-source-url'));
 if(form.id==='product-form')perform(async()=>{await api(`/api/products/${form.dataset.id}`,'PUT',{title:val('p-title'),description:val('p-description'),price:val('p-price'),sku:val('p-sku'),gtin:val('p-gtin')});return 'Product details saved.';});
 if(form.id==='policy-source-form')startSiteKitJob(val('source-store-url'));
 if(form.id==='page-form')perform(async()=>{await api(`/api/pages/${form.dataset.id}`,'PUT',{kind:val('page-kind'),title:val('page-title'),body:val('page-body')});return 'Page details saved.';});
});
const launchParams=new URLSearchParams(window.location.search);
const launchError=launchParams.get('shopify_error');
if(launchError){
 view='connections';
 window.addEventListener('load',()=>setTimeout(()=>showToast(launchError),600));
 window.history.replaceState({},document.title,window.location.pathname);
}else if(launchParams.has('shop')&&launchParams.has('host')){
 view='connections';
 window.addEventListener('load',()=>setTimeout(()=>showToast(
  'Shopify opened 4GMC without an API token. Publish the app as non-embedded with Legacy install flow enabled, then click Connect Shopify.'
 ),600));
 window.history.replaceState({},document.title,window.location.pathname);
}
setInterval(async()=>{if(!data||!(view==='tasks'||(data.jobs||[]).some(job=>['queued','running'].includes(job.status))))return;try{const result=await api('/api/jobs');data.jobs=result.jobs;data.task_capacity=result.capacity;if(view==='tasks')render();}catch{}},2000);
refresh().catch(error=>showToast(error?.message||error,true));
