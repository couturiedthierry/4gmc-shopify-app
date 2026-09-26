import sys

content = open('server.py', encoding='utf8').read()
start_str = 'async def generate_site_kit(data: SiteKitInput, progress=None):'
end_str = 'async def prepare_site_kit(data: SiteKitInput, request: Request):'
start_idx = content.find(start_str)
end_idx = content.find(end_str)
if start_idx == -1 or end_idx == -1:
    print('Not found')
    sys.exit(1)

new_func = '''async def generate_site_kit(data: SiteKitInput, progress=None):
    from static_pages.generator import generate_static_page
    import uuid, hashlib, json
    
    async with site_kit_lock():
        with db() as c:
            store = store_row(c)
            business = json.loads(store['business'])
            brand_val = store['brand']
            brand = json.loads(brand_val or '{}') if isinstance(brand_val, str) else (brand_val or {})
        required = ('business_name', 'domain_name', 'email', 'address', 'phone', 'country', 'currency')
        missing = [key.replace('_', ' ') for key in required if not str(business.get(key, '')).strip()]
        if missing:
            fail('Complete these Business & brand fields first: ' + ', '.join(missing))
            
        if progress:
            progress('Generating standard store pages and policies deterministically...', 0, 0)
            
        source_host = business.get('domain_name', 'example.com')
        
        target_kinds = [
            'shipping', 'returns', 'privacy', 'terms', 'contact_information', 
            'legal_notice', 'contact', 'faq', 'about_us', 
            'cancellation_policy', 'warranty_policy'
        ]
        
        items = []
        for kind in target_kinds:
            path = site_kit.POLICY_PATHS.get(kind, f'/pages/{kind.replace("_", "-")}')
            handle = kind.replace('_', '-') if kind in site_kit.POLICY_PATHS else kind.replace('_', '-')
            if kind == 'cancellation_policy':
                title = 'Order Cancellation Policy'
            elif kind == 'warranty_policy':
                title = 'Warranty Policy'
            else:
                title = SITE_KIT_TITLES.get(kind, kind.replace('_', ' ').title())
                
            items.append({
                'kind': kind, 
                'title': title,
                'source_url': f"https://{source_host}{path}",
                'handle': handle
            })
            
        generated_items = []
        completed_count = 0
        
        if progress:
            progress(f'Generating 0 of {len(items)} destination-brand pages...', 0, len(items))
            
        for item in items:
            kind = item['kind']
            title = item['title']
            
            body = generate_static_page(kind, business, brand, force_variant=None)
            
            guard = {
                'version': 3,
                'identity_hash': business_identity_hash(business),
                'content_hash': guarded_page_hash(title, body),
                'source_host': source_host,
                'source_digest': hashlib.sha256(b"STATIC_GENERATOR").hexdigest(),
            }
            generated_item = dict(item, title=title, body=body, brand_guard=json.dumps(guard))
            generated_items.append(generated_item)
            
            completed_count += 1
            if progress:
                progress(f'Generated {completed_count} of {len(items)} destination-brand pages...', completed_count, len(items))

            with db() as c:
                c.execute('DELETE FROM store_pages WHERE store_id = ? AND kind = ?', (store['id'], kind))
                c.execute(
                    'INSERT INTO store_pages (id, store_id, kind, handle, title, body, created_at, source_url, brand_guard) '
                    'VALUES (?, ?, ?, ?, ?, ?, datetime("now"), ?, ?)',
                    (str(uuid.uuid4()), store['id'], kind, item['handle'], title, body, item['source_url'], json.dumps(guard))
                )

        if progress:
            progress('Pages and policies generated and securely stored.', len(items), len(items))

        return {'pages': generated_items, 'skipped': []}

'''
content = content[:start_idx] + new_func + content[end_idx:]
open('server.py', 'w', encoding='utf8').write(content)
print('Done!')
