"""Shopify USA market and shipping setup for the 2026-07 Admin GraphQL API."""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation

CONTEXT_QUERY = '''query UsaStoreContext {
  shop { name contactEmail currencyCode features { marketDrivenShipping } }
  markets(first: 100, type: REGION) {
    pageInfo { hasNextPage }
    nodes { id name status conditions { regionsCondition {
      applicationLevel regions(first: 100) { pageInfo { hasNextPage }
        nodes { __typename ... on MarketRegionCountry { countryCode: code }
          ... on MarketRegionSubdivision { subdivisionCode: code country { code } } }
      }
    } } }
  }
}'''
MARKET_SHIPPING_QUERY = '''query UsaMarketShipping {
  markets(first: 100, type: REGION) { pageInfo { hasNextPage }
    nodes { id delivery { shipping { isEnabled
      optionDefinitions(first: 100) { pageInfo { hasNextPage }
        nodes { id isActive ... on DeliveryFlatRateOptionDefinition {
          name rateGroups(first: 100) { pageInfo { hasNextPage }
            nodes { rate { price { amount currencyCode } } }
          }
        } }
      }
    } } }
  }
}'''
PROFILES_QUERY = '''query UsaDeliveryProfiles {
  deliveryProfiles(first: 100, merchantOwnedOnly: true) { pageInfo { hasNextPage }
    nodes { id name profileLocationGroups { locationGroup { id }
      locationGroupZones(first: 100) { pageInfo { hasNextPage }
        nodes { zone { id countries { code { countryCode restOfWorld } provinces { code } } }
          methodDefinitions(first: 100) { pageInfo { hasNextPage }
            nodes { id active name methodConditions { field }
              rateProvider { __typename ... on DeliveryRateDefinition {
                price { amount currencyCode }
              } }
            }
          }
        }
      }
    } }
  }
}'''
MARKET_CREATE = '''mutation UsaMarketCreate($input: MarketCreateInput!) {
  marketCreate(input: $input) { market { id status } userErrors { field message } }
}'''
MARKET_UPDATE = '''mutation UsaMarketUpdate($id: ID!, $input: MarketUpdateInput!) {
  marketUpdate(id: $id, input: $input) { market { id status } userErrors { field message } }
}'''
PROFILE_UPDATE = '''mutation UsaProfileUpdate($id: ID!, $profile: DeliveryProfileInput!) {
  deliveryProfileUpdate(id: $id, profile: $profile) {
    profile { id } userErrors { field message }
  }
}'''


def nodes(connection):
    return (connection or {}).get('nodes') or []


def too_many(connection):
    return bool((connection or {}).get('pageInfo', {}).get('hasNextPage'))


def region_codes(market):
    condition = ((market.get('conditions') or {}).get('regionsCondition') or {})
    if condition.get('applicationLevel') == 'ALL':
        return ['*']
    regions = condition.get('regions') or {}
    if too_many(regions):
        raise ValueError('A market has more than 100 regions; inspect it in Shopify before changing markets.')
    result = []
    for item in nodes(regions):
        if item.get('__typename') == 'MarketRegionCountry':
            if not item.get('countryCode'):
                raise ValueError('Shopify returned a market country without a code.')
            result.append(item['countryCode'])
        elif item.get('__typename') == 'MarketRegionSubdivision':
            country = (item.get('country') or {}).get('code')
            subdivision = item.get('subdivisionCode')
            if not country or not subdivision:
                raise ValueError('Shopify returned a market subdivision without a code.')
            result.append(country + ':' + subdivision)
        else:
            raise ValueError('A market uses an unfamiliar region type; inspect it in Shopify first.')
    return result


def free_market_shipping_input(option_ids):
    return {'delivery': {'shipping': {
        'isEnabled': True,
        'optionDefinitionsToDelete': option_ids,
        'optionDefinitionsToCreate': [{'flatRate': {
            'name': 'Free shipping', 'currency': 'USD', 'isActive': True,
            'rateGroups': [{'rate': {'price': {'amount': '0.00', 'currencyCode': 'USD'}}}],
        }}],
    }}}


def legacy_profile_input(profile):
    groups = profile.get('profileLocationGroups') or []
    if not groups or len(groups) > 5:
        raise ValueError(f"Shipping profile {profile['name']} has no location group or more than five; inspect it in Shopify first.")
    delete_ids, updates = [], []
    for group in groups:
        zones = group.get('locationGroupZones') or {}
        if too_many(zones):
            raise ValueError(f"Shipping profile {profile['name']} has more than 100 zones.")
        delete_ids += [zone['zone']['id'] for zone in nodes(zones)]
        for zone in nodes(zones):
            if too_many(zone.get('methodDefinitions')):
                raise ValueError(f"Shipping profile {profile['name']} has more than 100 shipping methods in a zone.")
        updates.append({'id': group['locationGroup']['id'], 'zonesToCreate': [{
            'name': 'United States',
            'countries': [{'code': 'US', 'includeAllProvinces': True}],
            'methodDefinitionsToCreate': [{
                'name': 'Free shipping', 'active': True, 'currencyCode': 'USD',
                'rateGroupsToCreate': [{'rateDefinitionsToCreate': [{
                    'price': {'amount': '0.00', 'currencyCode': 'USD'},
                }]}],
            }],
        }]})
    return {'zonesToDelete': delete_ids, 'locationGroupsToUpdate': updates}


def build_plan(context, shipping, store):
    shop = context.get('shop') or {}
    markets = context.get('markets') or {}
    if too_many(markets):
        raise ValueError('The store has more than 100 region markets; inspect them in Shopify first.')
    if not isinstance(shop.get('features', {}).get('marketDrivenShipping'), bool):
        raise ValueError('Shopify did not report which shipping system this store uses.')
    merchant = json.loads(store['business'])
    desired_name = store['name'].strip()
    desired_email = str(merchant.get('email') or '').strip()
    if not desired_name or desired_name == 'My store' or not desired_email:
        raise ValueError('Enter the real store name and contact email in Business & brand first.')
    if str(merchant.get('country') or '').strip().upper() not in {'US', 'USA', 'UNITED STATES'}:
        raise ValueError('Set the target country to United States in Business & brand first.')
    if str(merchant.get('currency') or '').strip().upper() != 'USD':
        raise ValueError('Set the target currency to USD in Business & brand first.')
    if not str(merchant.get('shipping_time') or '').strip():
        raise ValueError('Enter a delivery estimate the store can actually fulfill before offering free shipping.')
    if shop.get('currencyCode') != 'USD':
        raise ValueError('Shopify base currency is not USD. The merchant must correct this in Shopify before USA setup.')
    region_markets = nodes(markets)
    exact_us = [m for m in region_markets if region_codes(m) == ['US']]
    if len(exact_us) > 1:
        raise ValueError('Multiple USA-only markets exist. Inspect them in Shopify before applying this setup.')
    target = exact_us[0] if exact_us else None
    other_active = [m for m in region_markets if m['status'] == 'ACTIVE' and (not target or m['id'] != target['id'])]
    market_shipping = bool(shop['features']['marketDrivenShipping'])
    profile_updates = []
    option_ids = []
    if market_shipping:
        shipping_markets = shipping.get('markets') or {}
        if too_many(shipping_markets):
            raise ValueError('Shopify returned more than 100 shipping markets.')
        live = next((m for m in nodes(shipping_markets) if target and m['id'] == target['id']), None)
        config = ((live or {}).get('delivery') or {}).get('shipping') or {}
        options = config.get('optionDefinitions') or {}
        if too_many(options):
            raise ValueError('The USA market has more than 100 shipping options.')
        option_ids = [o['id'] for o in nodes(options)]
    else:
        profiles = shipping.get('deliveryProfiles') or {}
        if too_many(profiles):
            raise ValueError('The store has more than 100 shipping profiles.')
        for profile in nodes(profiles):
            profile_updates.append({'id': profile['id'], 'name': profile['name'],
                                    'input': legacy_profile_input(profile)})
        if not profile_updates:
            raise ValueError('Shopify returned no merchant shipping profiles to update.')
    manual = []
    if shop.get('name', '').strip() != desired_name:
        manual.append(f"Shopify store name is '{shop.get('name','')}', but the workspace says '{desired_name}'. Only the merchant can change the actual name in Shopify Settings â†’ General.")
    if shop.get('contactEmail', '').casefold() != desired_email.casefold():
        manual.append('Shopify customer contact email differs from the workspace. Only the merchant can change it in Shopify Settings â†’ Notifications or General.')
    plan = {'shop': {'name':shop.get('name'), 'contactEmail':shop.get('contactEmail'), 'currencyCode':shop.get('currencyCode')},
            'target': {'country':'US', 'currency':'USD', 'shipping':'Free shipping (USD 0.00)'},
            'shipping_system':'markets' if market_shipping else 'delivery_profiles',
            'usa_market': {'id':target['id'], 'status':target['status']} if target else None,
            'markets_to_pause':[{'id':m['id'],'name':m['name']} for m in other_active],
            'shipping_to_replace':len(option_ids) if market_shipping else sum(len(p['input']['zonesToDelete']) for p in profile_updates),
            'shipping_profiles':[{'id':p['id'],'name':p['name']} for p in profile_updates],
            'manual_steps':manual}
    fingerprint = hashlib.sha256(json.dumps([context,shipping,store['name'],merchant],sort_keys=True).encode()).hexdigest()
    plan['fingerprint'] = fingerprint
    return plan, {'target':target,'other_active':other_active,'option_ids':option_ids,'profiles':profile_updates}


def market_shipping_verified(market):
    config = ((market.get('delivery') or {}).get('shipping') or {})
    options = config.get('optionDefinitions') or {}
    if not config.get('isEnabled') or too_many(options) or len(nodes(options)) != 1:
        return False
    item = nodes(options)[0]
    if not item.get('isActive') or item.get('name') != 'Free shipping':
        return False
    groups = item.get('rateGroups') or {}
    if too_many(groups) or len(nodes(groups)) != 1:
        return False
    price = (nodes(groups)[0].get('rate') or {}).get('price') or {}
    try:
        return Decimal(str(price.get('amount'))) == 0 and price.get('currencyCode') == 'USD'
    except InvalidOperation:
        return False


def legacy_shipping_verified(profiles):
    listed = nodes(profiles.get('deliveryProfiles'))
    if not listed or too_many(profiles.get('deliveryProfiles')):
        return False
    for profile in listed:
        if not profile.get('profileLocationGroups'):
            return False
        for group in profile.get('profileLocationGroups') or []:
            zones = nodes(group.get('locationGroupZones'))
            if len(zones) != 1:
                return False
            zone = zones[0]
            countries = (zone.get('zone') or {}).get('countries') or []
            if len(countries) != 1 or (countries[0].get('code') or {}).get('countryCode') != 'US' or (countries[0].get('code') or {}).get('restOfWorld'):
                return False
            methods = nodes(zone.get('methodDefinitions'))
            if len(methods) != 1 or methods[0].get('name') != 'Free shipping' or not methods[0].get('active'):
                return False
            if methods[0].get('methodConditions'):
                return False
            provider = methods[0].get('rateProvider') or {}
            if provider.get('__typename') != 'DeliveryRateDefinition':
                return False
            price = provider.get('price') or {}
            try:
                if Decimal(str(price.get('amount'))) != 0 or price.get('currencyCode') != 'USD':
                    return False
            except InvalidOperation:
                return False
    return True
