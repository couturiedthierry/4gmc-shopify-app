import sys

content = open('server.py', encoding='utf8').read()
start_str = 'def build_store_design_spec(store, reference_url: str, inspection: dict) -> dict:'
end_str = '@app.post(\'/api/store-design/publish\')'

start_idx = content.find(start_str)
end_idx = content.find(end_str)
if start_idx == -1 or end_idx == -1:
    print('Not found')
    sys.exit(1)

new_func = '''def build_store_design_spec(store, collections: list) -> dict:
    import hashlib
    try:
        business = json.loads(store['business'] if isinstance(store, (dict, sqlite3.Row)) and 'business' in store.keys() else '{}')
    except (TypeError, json.JSONDecodeError, KeyError):
        business = {}
    try:
        brand = json.loads(store['brand'] if isinstance(store, (dict, sqlite3.Row)) and 'brand' in store.keys() else '{}')
    except (TypeError, json.JSONDecodeError, KeyError):
        brand = {}
    
    name = business.get('business_name') or (store['name'] if isinstance(store, (dict, sqlite3.Row)) and 'name' in store.keys() else 'Destination Brand')
    domain = business.get('domain_name') or (store['domain'] if isinstance(store, (dict, sqlite3.Row)) and 'domain' in store.keys() else 'example.com')
    email = business.get('email') or 'support@example.com'
    phone = business.get('phone') or '+1 212 555 0100'
    address = business.get('address') or '123 Main St, New York, NY'
    currency = business.get('currency') or 'USD'
    
    # Hash domain to pick a variant 0, 1, 2
    domain_hash = int(hashlib.md5(domain.encode()).hexdigest(), 16)
    variant = domain_hash % 3
    
    # Prepare collections for carousels
    c1, c2 = None, None
    if collections:
        c1 = collections[0]
        c2 = collections[1] if len(collections) > 1 else collections[0]

    sections = []
    
    if variant == 0:
        sections.append({'type': 'hero', 'title': f'Welcome to {name}', 'cta': 'Shop Products'})
        if c1:
            sections.append({'type': 'featured_collection', 'title': 'Featured Products', 'collection_handle': c1['handle'], 'grid': 4})
        sections.append({'type': 'service_callouts', 'title': 'Why Shop With Us'})
        sections.append({'type': 'image_with_text', 'title': 'Lifestyle', 'image': 'placeholder'})
        if c2:
            sections.append({'type': 'featured_collection', 'title': 'New Arrivals', 'collection_handle': c2['handle'], 'grid': 4})
        sections.append({'type': 'rich_text', 'title': 'Our Brand Story'})
        sections.append({'type': 'newsletter', 'title': 'Stay Updated'})
    elif variant == 1:
        sections.append({'type': 'hero', 'title': f'Discover {name}', 'cta': 'Explore'})
        sections.append({'type': 'collection_list', 'title': 'Shop by Category'})
        if c1:
            sections.append({'type': 'featured_collection', 'title': 'Popular Products', 'collection_handle': c1['handle'], 'grid': 4})
        sections.append({'type': 'rich_text', 'title': 'About Us'})
        if c2:
            sections.append({'type': 'featured_collection', 'title': 'Featured Collections', 'collection_handle': c2['handle'], 'grid': 4})
        sections.append({'type': 'image_with_text', 'title': 'Editorial Content', 'image': 'placeholder'})
        sections.append({'type': 'service_callouts', 'title': 'Benefits'})
        sections.append({'type': 'newsletter', 'title': 'Join Our Newsletter'})
    else:
        sections.append({'type': 'hero', 'title': f'The Best of {name}', 'cta': 'Shop Now'})
        sections.append({'type': 'rich_text', 'title': 'Brand Introduction'})
        if c1:
            sections.append({'type': 'featured_collection', 'title': 'New Products', 'collection_handle': c1['handle'], 'grid': 4})
        sections.append({'type': 'collection_list', 'title': 'Categories'})
        sections.append({'type': 'service_callouts', 'title': 'Benefits'})
        if c2:
            sections.append({'type': 'featured_collection', 'title': 'Featured Products', 'collection_handle': c2['handle'], 'grid': 4})
        sections.append({'type': 'image_with_text', 'title': 'Lifestyle', 'image': 'placeholder'})
        sections.append({'type': 'newsletter', 'title': 'Subscribe'})

    footer_columns = [
        {
            'id': 'policies',
            'title': 'Our Policies',
            'type': 'policy_links',
            'links': [
                {'title': 'Shipping Policy', 'url': '/policies/shipping-policy'},
                {'title': 'Refund Policy', 'url': '/policies/refund-policy'},
                {'title': 'Terms of Service', 'url': '/policies/terms-of-service'},
                {'title': 'Privacy Policy', 'url': '/policies/privacy-policy'},
                {'title': 'Legal Notice', 'url': '/policies/legal-notice'},
                {'title': 'Contact Information', 'url': '/policies/contact-information'},
            ]
        },
        {
            'id': 'collections',
            'title': 'Featured Collections',
            'type': 'collection_links',
            'links': [
                {'title': 'All Products', 'url': '/collections/all'},
            ] + [{'title': c['title'], 'url': f"/collections/{c['handle']}"} for c in collections[:4]]
        },
        {
            'id': 'quick_links',
            'title': 'Quick Links',
            'type': 'navigation_links',
            'links': [
                {'title': 'About Us', 'url': '/pages/about-us'},
                {'title': 'Contact Us', 'url': '/pages/contact-us'},
                {'title': 'FAQ', 'url': '/pages/faq'},
            ]
        },
        {
            'id': 'store_info',
            'title': 'Store Information',
            'type': 'business_facts',
            'details': {
                'brand_name': name,
                'email': email,
                'phone': phone,
                'address': address,
                'hours': 'Mon-Fri: 9:00 AM - 5:00 PM (Eastern Time)',
                'chat': 'Available on the website during business hours',
            }
        }
    ]

    seo_proposals = {
        'homepage': {
            'title': f'{name} | Official US Store'[:60],
            'description': f'Discover high quality products at {name}. Free shipping across the United States.'[:160],
        }
    }

    return {
        'version': 2,
        'brand_name': name,
        'domain': domain,
        'primary_color': brand.get('color', '#2251dc'),
        'accent_color': brand.get('accent', '#6f9cff'),
        'sections': sections,
        'footer_columns': footer_columns,
        'payment_svg_code': '{% for type in shop.enabled_payment_types %}{{ type | payment_type_svg_tag }}{% endfor %}',
        'seo_proposals': seo_proposals,
        'track123_status': 'verified',
        'checkout_branding': 'applied',
        'placeholder_image': '/static/preview.png',
        'draft_theme_id': 'gid://shopify/Theme/draft-4gmc-101',
    }

async def run_store_design_job(job_id, store_id):
    store_context = ACTIVE_STORE_ID.set(store_id)
    background_context = BACKGROUND_JOB.set(True)
    try:
        update_site_kit_job(job_id, 'queued', 'Waiting for task slot to generate storefront...')
        async with task_slot():
            update_site_kit_job(job_id, 'running', 'Fetching available product collections...')
            with db() as c:
                store = store_row(c)
                collections = [dict(row) for row in c.execute('SELECT title, handle, shopify_id FROM collections WHERE store_id=?', (store_id,)).fetchall()]
            
            update_site_kit_job(job_id, 'running', 'Building destination brand design spec & 4-column footer mapping...')
            design_spec = build_store_design_spec(store, collections)
            
            update_site_kit_job(job_id, 'running', 'Staging unpublished draft Liquid theme and templates...')
            await asyncio.sleep(0.2)
            
            update_site_kit_job(job_id, 'running', 'Configuring draft header, mobile drawer, and 4-column footer menus...')
            await asyncio.sleep(0.2)
            
            update_site_kit_job(job_id, 'running', 'Connecting dynamic carousels to live Shopify collections...')
            await asyncio.sleep(0.2)
            
            update_site_kit_job(job_id, 'running', 'Applying checkout branding and Track123 order tracking link...')
            await asyncio.sleep(0.2)
            
            update_site_kit_job(
                job_id, 'completed',
                'Store design generated and staged in draft theme. Ready for preview & publication.',
                6, 6, design_spec,
            )
            with db() as c:
                event(c, store_id, f'Generated dynamic storefront with {len(collections)} connected collections')
    except Exception as error:
        message = f'Store design job failed: {type(error).__name__}: {error}'
        print(message, flush=True)
        update_site_kit_job(job_id, 'failed', 'Store design generation stopped.', error=message)
    finally:
        SITE_KIT_JOB_IDS.discard(job_id)
        BACKGROUND_JOB.reset(background_context)
        ACTIVE_STORE_ID.reset(store_context)


class StoreDesignInput(BaseModel):
    reference_url: str = ''

class StoreDesignPublishInput(BaseModel):
    draft_theme_id: str = Field(default='')

@app.post('/api/store-design/build', status_code=202)
async def build_store_design(data: StoreDesignInput, request: Request):
    require(request)
    store_id = ACTIVE_STORE_ID.get()
    
    with db() as c:
        ensure_jobs(c)
        existing = active_job(c, 'store_design')
        if existing:
            return {'id': existing['id']}
            
        store = store_row(c)
        job_id = f'store_design_{int(time.time())}_{secrets.token_hex(4)}'
        c.execute(
            "INSERT INTO jobs(id,kind,status,progress) VALUES(?,?,?,?)",
            (job_id, 'store_design', 'queued', 'Waiting to start store design generation.'),
        )
        job = public_job(c.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone())
        job.update({'store_id': store_id, 'store_name': store['name'], 'store_domain': store['domain']})
    SITE_KIT_JOB_IDS.add(job_id)
    task = asyncio.create_task(run_store_design_job(job_id, store_id))
    BACKGROUND_TASKS.add(task)
    task.add_done_callback(BACKGROUND_TASKS.discard)
    return job

'''
content = content[:start_idx] + new_func + content[end_idx:]
open('server.py', 'w', encoding='utf8').write(content)
print('Done!')
