# Field Definitions

Complete field-level specifications for all snapshot files.

---

## Conventions

- **Required**: Field must always be present (may be null)
- **Optional**: Field may be omitted
- **Type**: JSON type (string, number, boolean, array, object, null)
- **Enum**: Fixed set of allowed values
- **Micros**: Currency in micros (1,000,000 = $1.00)

---

## Metadata Files

### _manifest.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `snapshot_id` | string | yes | Unique snapshot identifier (timestamp) | `"2026-01-15T143052Z"` |
| `created_at` | string | yes | ISO 8601 timestamp with microseconds | `"2026-01-15T14:30:52.123456Z"` |
| `duration_seconds` | number | yes | Total time to complete snapshot | `47.3` |
| `accounts.google_ads.customer_id` | string | yes | Google Ads customer ID (no hyphens) | `"1234567890"` |
| `accounts.google_ads.login_customer_id` | string | no | MCC login ID if applicable | `"9876543210"` |
| `accounts.merchant_center.account_id` | string | yes | Merchant Center account ID | `"5308355318"` |
| `api_versions.google_ads` | string | yes | Google Ads API version used | `"v19"` |
| `api_versions.merchant_center` | string | yes | Merchant API version used | `"v1beta"` |
| `file_counts.raw` | number | yes | Number of raw files written | `16` |
| `file_counts.normalized` | number | yes | Number of normalized files written | `12` |
| `record_counts` | object | yes | Record counts by entity type | `{"campaigns": 5}` |
| `errors` | array | yes | Any errors encountered during dump | `[]` |

### _index.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `campaigns.by_id` | object | yes | Map of campaign ID → name | `{"123": "Branded"}` |
| `campaigns.by_type` | object | yes | Map of type → campaign IDs | `{"SEARCH": ["123"]}` |
| `campaigns.by_status` | object | yes | Map of status → campaign IDs | `{"ENABLED": ["123"]}` |
| `products.by_brand` | object | yes | Count of products per brand | `{"Goodman": 479}` |
| `products.by_status` | object | yes | Count by eligibility status | `{"eligible": 1109}` |
| `totals` | object | yes | Total counts per entity type | `{"campaigns": 5}` |

---

## Google Ads — Campaigns

### raw/ads/campaigns.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `extracted_at` | string | yes | ISO 8601 extraction timestamp | `"2026-01-15T14:30:52Z"` |
| `account_id` | string | yes | Google Ads customer ID | `"1234567890"` |
| `count` | number | yes | Number of records | `5` |
| `records` | array | yes | Array of campaign objects | `[...]` |

#### Campaign Record (raw)

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `resource_name` | string | yes | Full resource name | `"customers/123/campaigns/456"` |
| `id` | string | yes | Campaign ID | `"456"` |
| `name` | string | yes | Campaign name | `"Branded - Exact Match"` |
| `status` | string | yes | Enum: ENABLED, PAUSED, REMOVED | `"ENABLED"` |
| `advertising_channel_type` | string | yes | Enum: SEARCH, DISPLAY, SHOPPING, PERFORMANCE_MAX, etc. | `"SEARCH"` |
| `advertising_channel_sub_type` | string | no | Sub-type if applicable | `null` |
| `bidding_strategy_type` | string | yes | Enum: TARGET_ROAS, TARGET_CPA, MAXIMIZE_CONVERSIONS, MANUAL_CPC, etc. | `"TARGET_ROAS"` |
| `bidding_strategy` | string | no | Resource name of portfolio strategy | `null` |
| `target_roas.target_roas` | number | no | Target ROAS value (if applicable) | `4.0` |
| `target_cpa.target_cpa_micros` | number | no | Target CPA in micros | `5000000` |
| `campaign_budget` | string | yes | Budget resource name | `"customers/123/campaignBudgets/789"` |
| `start_date` | string | yes | YYYY-MM-DD | `"2024-01-01"` |
| `end_date` | string | no | YYYY-MM-DD or null | `null` |
| `labels` | array | yes | Array of label resource names | `["customers/123/labels/111"]` |
| `network_settings.target_google_search` | boolean | yes | Target Google Search | `true` |
| `network_settings.target_search_network` | boolean | yes | Target Search Partners | `false` |
| `network_settings.target_content_network` | boolean | yes | Target Display Network | `false` |
| `geo_target_type_setting.positive_geo_target_type` | string | no | Enum: PRESENCE_OR_INTEREST, PRESENCE | `"PRESENCE"` |
| `geo_target_type_setting.negative_geo_target_type` | string | no | Enum: PRESENCE_OR_INTEREST, PRESENCE | `"PRESENCE"` |

### normalized/ads/campaigns.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `id` | string | yes | Campaign ID only | `"456"` |
| `name` | string | yes | Campaign name | `"Branded - Exact Match"` |
| `type` | string | yes | Normalized: SEARCH, DISPLAY, SHOPPING, PMAX | `"SEARCH"` |
| `status` | string | yes | Normalized: ENABLED, PAUSED, REMOVED | `"ENABLED"` |
| `bidding_strategy` | string | yes | Normalized strategy name | `"TARGET_ROAS"` |
| `bidding_target` | number | no | Target value (ROAS or CPA as dollars) | `4.0` |
| `budget_id` | string | yes | Budget ID only | `"789"` |
| `budget_amount_micros` | number | yes | Daily budget in micros | `50000000` |
| `budget_delivery` | string | yes | Normalized: STANDARD, ACCELERATED | `"STANDARD"` |
| `start_date` | string | yes | YYYY-MM-DD | `"2024-01-01"` |
| `end_date` | string | no | YYYY-MM-DD or null | `null` |
| `labels` | array | yes | Array of label names (not IDs) | `["branded"]` |

---

## Google Ads — Ad Groups

### raw/ads/ad_groups.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `extracted_at` | string | yes | ISO 8601 extraction timestamp | `"2026-01-15T14:30:52Z"` |
| `count` | number | yes | Number of records | `42` |
| `records` | array | yes | Array of ad group objects | `[...]` |

#### Ad Group Record (raw)

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `resource_name` | string | yes | Full resource name | `"customers/123/adGroups/456"` |
| `id` | string | yes | Ad group ID | `"456"` |
| `name` | string | yes | Ad group name | `"Goodman Furnaces"` |
| `campaign` | string | yes | Campaign resource name | `"customers/123/campaigns/789"` |
| `status` | string | yes | Enum: ENABLED, PAUSED, REMOVED | `"ENABLED"` |
| `type` | string | yes | Enum: SEARCH_STANDARD, DISPLAY_STANDARD, etc. | `"SEARCH_STANDARD"` |
| `cpc_bid_micros` | number | no | Default CPC bid | `2500000` |
| `target_cpa_micros` | number | no | Target CPA for this ad group | `null` |
| `target_roas` | number | no | Target ROAS for this ad group | `null` |
| `labels` | array | yes | Array of label resource names | `[]` |

### normalized/ads/ad_groups.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `id` | string | yes | Ad group ID | `"456"` |
| `campaign_id` | string | yes | Parent campaign ID | `"789"` |
| `name` | string | yes | Ad group name | `"Goodman Furnaces"` |
| `status` | string | yes | Normalized: ENABLED, PAUSED, REMOVED | `"ENABLED"` |
| `type` | string | yes | Normalized type | `"SEARCH"` |
| `cpc_bid_micros` | number | no | Default CPC bid | `2500000` |
| `labels` | array | yes | Array of label names | `[]` |

---

## Google Ads — Keywords

### raw/ads/keywords.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `extracted_at` | string | yes | ISO 8601 extraction timestamp | `"2026-01-15T14:30:52Z"` |
| `count` | number | yes | Number of records | `387` |
| `records` | array | yes | Array of keyword objects | `[...]` |

#### Keyword Record (raw)

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `resource_name` | string | yes | Full resource name | `"customers/123/adGroupCriteria/456~789"` |
| `criterion_id` | string | yes | Criterion ID | `"789"` |
| `ad_group` | string | yes | Ad group resource name | `"customers/123/adGroups/456"` |
| `keyword.text` | string | yes | Keyword text | `"goodman furnace"` |
| `keyword.match_type` | string | yes | Enum: EXACT, PHRASE, BROAD | `"EXACT"` |
| `status` | string | yes | Enum: ENABLED, PAUSED, REMOVED | `"ENABLED"` |
| `cpc_bid_micros` | number | no | Keyword-level bid override | `null` |
| `quality_info.quality_score` | number | no | 1-10 quality score | `8` |
| `quality_info.creative_quality_score` | string | no | Enum: BELOW_AVERAGE, AVERAGE, ABOVE_AVERAGE | `"AVERAGE"` |
| `quality_info.post_click_quality_score` | string | no | Landing page experience | `"ABOVE_AVERAGE"` |
| `quality_info.search_predicted_ctr` | string | no | Expected CTR | `"ABOVE_AVERAGE"` |
| `labels` | array | yes | Array of label resource names | `[]` |

### normalized/ads/keywords.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `id` | string | yes | Criterion ID | `"789"` |
| `ad_group_id` | string | yes | Parent ad group ID | `"456"` |
| `campaign_id` | string | yes | Parent campaign ID | `"123"` |
| `text` | string | yes | Keyword text | `"goodman furnace"` |
| `match_type` | string | yes | Normalized: EXACT, PHRASE, BROAD | `"EXACT"` |
| `status` | string | yes | Normalized: ENABLED, PAUSED, REMOVED | `"ENABLED"` |
| `cpc_bid_micros` | number | no | Keyword bid or null | `null` |
| `quality_score` | number | no | 1-10 or null | `8` |
| `expected_ctr` | string | no | Normalized rating | `"ABOVE_AVERAGE"` |
| `ad_relevance` | string | no | Normalized rating | `"AVERAGE"` |
| `landing_page_exp` | string | no | Normalized rating | `"ABOVE_AVERAGE"` |

---

## Google Ads — Negative Keywords

### raw/ads/campaign_negatives.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `extracted_at` | string | yes | ISO 8601 extraction timestamp | `"2026-01-15T14:30:52Z"` |
| `count` | number | yes | Number of records | `87` |
| `records` | array | yes | Array of negative keyword objects | `[...]` |

#### Campaign Negative Record

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `resource_name` | string | yes | Full resource name | `"customers/123/campaignCriteria/456~789"` |
| `criterion_id` | string | yes | Criterion ID | `"789"` |
| `campaign` | string | yes | Campaign resource name | `"customers/123/campaigns/456"` |
| `keyword.text` | string | yes | Negative keyword text | `"free"` |
| `keyword.match_type` | string | yes | Enum: EXACT, PHRASE, BROAD | `"BROAD"` |
| `negative` | boolean | yes | Always true for negatives | `true` |

### raw/ads/adgroup_negatives.json

Same structure as campaign_negatives.json but with `ad_group` field instead of `campaign`.

### normalized/ads/negatives.json (Combined)

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `id` | string | yes | Criterion ID | `"789"` |
| `level` | string | yes | Enum: CAMPAIGN, ADGROUP | `"CAMPAIGN"` |
| `campaign_id` | string | yes | Parent campaign ID | `"456"` |
| `ad_group_id` | string | no | Ad group ID if level=ADGROUP | `null` |
| `text` | string | yes | Negative keyword text | `"free"` |
| `match_type` | string | yes | Normalized: EXACT, PHRASE, BROAD | `"BROAD"` |

---

## Google Ads — Ads (RSA)

### raw/ads/ads.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `extracted_at` | string | yes | ISO 8601 extraction timestamp | `"2026-01-15T14:30:52Z"` |
| `count` | number | yes | Number of records | `58` |
| `records` | array | yes | Array of ad objects | `[...]` |

#### Ad Record (raw)

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `resource_name` | string | yes | Full resource name | `"customers/123/ads/456"` |
| `id` | string | yes | Ad ID | `"456"` |
| `ad_group` | string | yes | Ad group resource name | `"customers/123/adGroups/789"` |
| `type` | string | yes | Enum: RESPONSIVE_SEARCH_AD, etc. | `"RESPONSIVE_SEARCH_AD"` |
| `status` | string | yes | Enum: ENABLED, PAUSED, REMOVED | `"ENABLED"` |
| `final_urls` | array | yes | Array of final URLs | `["https://example.com"]` |
| `responsive_search_ad.headlines` | array | yes | Array of headline objects | `[{"text": "Buy Now", "pinned_field": null}]` |
| `responsive_search_ad.descriptions` | array | yes | Array of description objects | `[{"text": "Free Shipping", "pinned_field": null}]` |
| `policy_summary.approval_status` | string | no | Approval status | `"APPROVED"` |
| `policy_summary.review_status` | string | no | Review status | `"REVIEWED"` |

### normalized/ads/ads.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `id` | string | yes | Ad ID | `"456"` |
| `ad_group_id` | string | yes | Parent ad group ID | `"789"` |
| `campaign_id` | string | yes | Parent campaign ID | `"123"` |
| `type` | string | yes | Normalized: RSA, ETA, etc. | `"RSA"` |
| `status` | string | yes | Normalized: ENABLED, PAUSED, REMOVED | `"ENABLED"` |
| `final_url` | string | yes | Primary final URL | `"https://example.com"` |
| `headlines` | array | yes | Array of headline strings | `["Buy Now", "Free Shipping"]` |
| `descriptions` | array | yes | Array of description strings | `["Shop today"]` |
| `approval_status` | string | no | Normalized: APPROVED, DISAPPROVED, PENDING | `"APPROVED"` |

---

## Google Ads — Assets

### raw/ads/assets.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `extracted_at` | string | yes | ISO 8601 extraction timestamp | `"2026-01-15T14:30:52Z"` |
| `count` | number | yes | Number of records | `34` |
| `records` | array | yes | Array of asset objects | `[...]` |

#### Asset Record (raw)

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `resource_name` | string | yes | Full resource name | `"customers/123/assets/456"` |
| `id` | string | yes | Asset ID | `"456"` |
| `type` | string | yes | Enum: SITELINK, CALLOUT, STRUCTURED_SNIPPET, CALL, IMAGE, etc. | `"SITELINK"` |
| `name` | string | no | Asset name if set | `"Free Shipping Sitelink"` |
| `sitelink_asset.link_text` | string | no | Sitelink text | `"Free Shipping"` |
| `sitelink_asset.description1` | string | no | First description | `"On orders over $99"` |
| `sitelink_asset.description2` | string | no | Second description | `"Shop now"` |
| `sitelink_asset.final_urls` | array | no | Final URLs | `["https://example.com/shipping"]` |
| `callout_asset.callout_text` | string | no | Callout text | `"24/7 Support"` |
| `structured_snippet_asset.header` | string | no | Header type | `"Brands"` |
| `structured_snippet_asset.values` | array | no | Snippet values | `["Goodman", "Rheem"]` |
| `call_asset.phone_number` | string | no | Phone number | `"+18005551234"` |
| `policy_summary.approval_status` | string | no | Approval status | `"APPROVED"` |

### raw/ads/asset_links.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `extracted_at` | string | yes | ISO 8601 extraction timestamp | `"2026-01-15T14:30:52Z"` |
| `count` | number | yes | Number of records | `78` |
| `records` | array | yes | Array of link objects | `[...]` |

#### Asset Link Record

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `resource_name` | string | yes | Full resource name | `"customers/123/campaignAssets/456~789"` |
| `asset` | string | yes | Asset resource name | `"customers/123/assets/789"` |
| `campaign` | string | no | Campaign resource name (if campaign-level) | `"customers/123/campaigns/456"` |
| `ad_group` | string | no | Ad group resource name (if adgroup-level) | `null` |
| `field_type` | string | yes | Enum: SITELINK, CALLOUT, STRUCTURED_SNIPPET, CALL | `"SITELINK"` |
| `status` | string | yes | Enum: ENABLED, PAUSED, REMOVED | `"ENABLED"` |

### normalized/ads/assets.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `id` | string | yes | Asset ID | `"456"` |
| `type` | string | yes | Normalized: SITELINK, CALLOUT, SNIPPET, CALL, IMAGE | `"SITELINK"` |
| `name` | string | no | Asset name | `"Free Shipping Sitelink"` |
| `text` | string | no | Primary text content | `"Free Shipping"` |
| `description` | string | no | Description if applicable | `"On orders over $99"` |
| `url` | string | no | Final URL if applicable | `"https://example.com/shipping"` |
| `linked_campaigns` | array | yes | Array of campaign IDs using this asset | `["456", "789"]` |
| `linked_ad_groups` | array | yes | Array of ad group IDs using this asset | `[]` |
| `approval_status` | string | no | Normalized: APPROVED, DISAPPROVED, PENDING | `"APPROVED"` |

---

## Google Ads — Change History

### raw/ads/change_history.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `extracted_at` | string | yes | ISO 8601 extraction timestamp | `"2026-01-15T14:30:52Z"` |
| `lookback_days` | number | yes | Days of history fetched | `14` |
| `count` | number | yes | Number of records | `234` |
| `records` | array | yes | Array of change event objects | `[...]` |

#### Change Event Record

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `change_date_time` | string | yes | ISO 8601 timestamp | `"2026-01-14T09:23:45Z"` |
| `change_resource_type` | string | yes | Resource type affected | `"CAMPAIGN"` |
| `change_resource_name` | string | yes | Resource name affected | `"customers/123/campaigns/456"` |
| `resource_change_operation` | string | yes | Enum: CREATE, UPDATE, REMOVE | `"UPDATE"` |
| `changed_fields` | array | no | Fields that changed | `["status", "budget"]` |
| `old_resource` | object | no | Previous state (partial) | `{"status": "ENABLED"}` |
| `new_resource` | object | no | New state (partial) | `{"status": "PAUSED"}` |
| `user_email` | string | no | User who made change | `"user@example.com"` |
| `client_type` | string | no | Client used | `"GOOGLE_ADS_WEB_CLIENT"` |
| `feed` | string | no | Feed if applicable | `null` |

### normalized/ads/change_history.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `timestamp` | string | yes | ISO 8601 timestamp | `"2026-01-14T09:23:45Z"` |
| `resource_type` | string | yes | Normalized: CAMPAIGN, ADGROUP, KEYWORD, etc. | `"CAMPAIGN"` |
| `resource_id` | string | yes | Resource ID | `"456"` |
| `resource_name` | string | no | Human-readable name | `"Branded - Exact Match"` |
| `operation` | string | yes | Normalized: CREATE, UPDATE, REMOVE | `"UPDATE"` |
| `fields_changed` | array | yes | List of changed fields | `["status"]` |
| `old_values` | object | no | Previous values | `{"status": "ENABLED"}` |
| `new_values` | object | no | New values | `{"status": "PAUSED"}` |
| `actor` | string | no | Who made the change | `"user@example.com"` |
| `source` | string | no | Normalized: UI, API, RULES, SYSTEM | `"UI"` |

---

## Google Ads — Performance

### raw/ads/performance.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `extracted_at` | string | yes | ISO 8601 extraction timestamp | `"2026-01-15T14:30:52Z"` |
| `date_range.start` | string | yes | YYYY-MM-DD | `"2026-01-01"` |
| `date_range.end` | string | yes | YYYY-MM-DD | `"2026-01-15"` |
| `by_campaign` | array | yes | Daily metrics by campaign | `[...]` |
| `by_ad_group` | array | yes | Daily metrics by ad group | `[...]` |

#### Performance Record

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `date` | string | yes | YYYY-MM-DD | `"2026-01-14"` |
| `campaign_id` | string | yes | Campaign ID | `"456"` |
| `ad_group_id` | string | no | Ad group ID (if by_ad_group) | `"789"` |
| `impressions` | number | yes | Impression count | `12345` |
| `clicks` | number | yes | Click count | `234` |
| `cost_micros` | number | yes | Cost in micros | `123456789` |
| `conversions` | number | yes | Conversion count | `12.5` |
| `conversions_value` | number | yes | Conversion value | `2345.67` |
| `all_conversions` | number | yes | All conversions (incl. cross-device) | `14.2` |
| `all_conversions_value` | number | yes | All conversions value | `2678.90` |

### normalized/ads/performance.json

Same structure as raw but with derived fields:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `ctr` | number | yes | Click-through rate | `0.019` |
| `cpc` | number | yes | Cost per click (dollars) | `5.28` |
| `cost` | number | yes | Cost (dollars) | `123.46` |
| `roas` | number | no | Return on ad spend | `4.23` |
| `conv_rate` | number | no | Conversion rate | `0.053` |
| `cpa` | number | no | Cost per acquisition | `9.88` |

---

## Performance Max — Campaigns

### raw/pmax/campaigns.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `extracted_at` | string | yes | ISO 8601 extraction timestamp | `"2026-01-15T14:30:52Z"` |
| `count` | number | yes | Number of records | `2` |
| `records` | array | yes | Array of PMax campaign objects | `[...]` |

#### PMax Campaign Record

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `resource_name` | string | yes | Full resource name | `"customers/123/campaigns/456"` |
| `id` | string | yes | Campaign ID | `"456"` |
| `name` | string | yes | Campaign name | `"PMax - Shopping"` |
| `status` | string | yes | Enum: ENABLED, PAUSED, REMOVED | `"ENABLED"` |
| `bidding_strategy_type` | string | yes | Usually MAXIMIZE_CONVERSION_VALUE | `"MAXIMIZE_CONVERSION_VALUE"` |
| `target_roas.target_roas` | number | no | Target ROAS if set | `4.0` |
| `campaign_budget` | string | yes | Budget resource name | `"customers/123/campaignBudgets/789"` |
| `shopping_setting.merchant_id` | string | no | Linked Merchant Center ID | `"5308355318"` |
| `shopping_setting.feed_label` | string | no | Feed label filter | `null` |
| `url_expansion_opt_out` | boolean | no | Whether URL expansion is disabled | `false` |

### normalized/pmax/campaigns.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `id` | string | yes | Campaign ID | `"456"` |
| `name` | string | yes | Campaign name | `"PMax - Shopping"` |
| `status` | string | yes | Normalized: ENABLED, PAUSED, REMOVED | `"ENABLED"` |
| `bidding_strategy` | string | yes | Bidding strategy name | `"MAXIMIZE_CONVERSION_VALUE"` |
| `target_roas` | number | no | Target ROAS if set | `4.0` |
| `budget_amount_micros` | number | yes | Daily budget in micros | `100000000` |
| `merchant_id` | string | no | Linked Merchant Center ID | `"5308355318"` |
| `url_expansion_enabled` | boolean | yes | Whether URL expansion is on | `true` |

---

## Performance Max — Asset Groups

### raw/pmax/asset_groups.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `extracted_at` | string | yes | ISO 8601 extraction timestamp | `"2026-01-15T14:30:52Z"` |
| `count` | number | yes | Number of records | `4` |
| `records` | array | yes | Array of asset group objects | `[...]` |

#### Asset Group Record

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `resource_name` | string | yes | Full resource name | `"customers/123/assetGroups/456"` |
| `id` | string | yes | Asset group ID | `"456"` |
| `campaign` | string | yes | Campaign resource name | `"customers/123/campaigns/789"` |
| `name` | string | yes | Asset group name | `"Goodman Products"` |
| `status` | string | yes | Enum: ENABLED, PAUSED, REMOVED | `"ENABLED"` |
| `final_urls` | array | yes | Final URLs | `["https://example.com/goodman"]` |
| `final_mobile_urls` | array | no | Mobile URLs | `[]` |
| `path1` | string | no | Display path 1 | `"goodman"` |
| `path2` | string | no | Display path 2 | `"hvac"` |
| `ad_strength` | string | no | Enum: EXCELLENT, GOOD, AVERAGE, POOR | `"GOOD"` |

### normalized/pmax/asset_groups.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `id` | string | yes | Asset group ID | `"456"` |
| `campaign_id` | string | yes | Parent campaign ID | `"789"` |
| `name` | string | yes | Asset group name | `"Goodman Products"` |
| `status` | string | yes | Normalized: ENABLED, PAUSED, REMOVED | `"ENABLED"` |
| `final_url` | string | yes | Primary final URL | `"https://example.com/goodman"` |
| `ad_strength` | string | no | Normalized: EXCELLENT, GOOD, AVERAGE, POOR | `"GOOD"` |
| `asset_counts` | object | yes | Count of assets by type | `{"HEADLINE": 5, "DESCRIPTION": 3}` |

---

## Performance Max — Listing Groups

### raw/pmax/listing_groups.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `extracted_at` | string | yes | ISO 8601 extraction timestamp | `"2026-01-15T14:30:52Z"` |
| `count` | number | yes | Number of records | `24` |
| `records` | array | yes | Array of listing group filter objects | `[...]` |

#### Listing Group Filter Record

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `resource_name` | string | yes | Full resource name | `"customers/123/assetGroupListingGroupFilters/456"` |
| `asset_group` | string | yes | Asset group resource name | `"customers/123/assetGroups/789"` |
| `id` | string | yes | Filter ID | `"456"` |
| `type` | string | yes | Enum: SUBDIVISION, UNIT_INCLUDED, UNIT_EXCLUDED | `"UNIT_INCLUDED"` |
| `case_value.product_brand.value` | string | no | Brand filter | `"Goodman"` |
| `case_value.product_category.category_id` | string | no | Category ID | `"12345"` |
| `case_value.product_custom_attribute.value` | string | no | Custom attribute | `null` |
| `case_value.product_type.value` | string | no | Product type | `null` |
| `parent_listing_group_filter` | string | no | Parent filter resource | `"customers/123/assetGroupListingGroupFilters/111"` |

---

## Merchant Center — Products

### raw/merchant/products.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `extracted_at` | string | yes | ISO 8601 extraction timestamp | `"2026-01-15T14:30:52Z"` |
| `account_id` | string | yes | Merchant Center account ID | `"5308355318"` |
| `count` | number | yes | Number of records | `1763` |
| `records` | array | yes | Array of product objects | `[...]` |

#### Product Record (raw)

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `name` | string | yes | Full resource name | `"accounts/123/products/online~en~US~SKU123"` |
| `offerId` | string | yes | Merchant's product ID | `"SKU123"` |
| `channel` | string | yes | Enum: ONLINE, LOCAL | `"ONLINE"` |
| `contentLanguage` | string | yes | Content language | `"en"` |
| `feedLabel` | string | yes | Feed label | `"US"` |
| `attributes.title` | string | yes | Product title | `"Goodman 3 Ton AC"` |
| `attributes.description` | string | no | Product description | `"High efficiency..."` |
| `attributes.link` | string | yes | Product page URL | `"https://example.com/product"` |
| `attributes.imageLink` | string | yes | Main image URL | `"https://example.com/image.jpg"` |
| `attributes.brand` | string | no | Brand name | `"Goodman"` |
| `attributes.gtin` | string | no | GTIN/UPC | `"123456789012"` |
| `attributes.mpn` | string | no | Manufacturer part number | `"GSX140361"` |
| `attributes.price.amountMicros` | string | yes | Price in micros | `"1299000000"` |
| `attributes.price.currencyCode` | string | yes | Currency | `"USD"` |
| `attributes.availability` | string | yes | Enum: in_stock, out_of_stock, preorder | `"in_stock"` |
| `attributes.condition` | string | yes | Enum: new, refurbished, used | `"new"` |
| `attributes.productTypes` | array | no | Product type taxonomy | `["HVAC > Air Conditioners"]` |
| `attributes.customLabel0` | string | no | Custom label 0 | `"equipment"` |
| `attributes.customLabel1` | string | no | Custom label 1 | `"goodman"` |
| `attributes.customLabel2` | string | no | Custom label 2 | `"ac"` |
| `attributes.customLabel3` | string | no | Custom label 3 | `null` |
| `attributes.customLabel4` | string | no | Custom label 4 | `null` |
| `attributes.excludedDestinations` | array | no | Excluded destinations | `["Shopping_ads"]` |
| `attributes.includedDestinations` | array | no | Included destinations | `["Free_listings"]` |

### normalized/merchant/products.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `id` | string | yes | Full product ID | `"online~en~US~SKU123"` |
| `offer_id` | string | yes | Merchant's product ID | `"SKU123"` |
| `title` | string | yes | Product title | `"Goodman 3 Ton AC"` |
| `brand` | string | no | Brand name | `"Goodman"` |
| `gtin` | string | no | GTIN/UPC | `"123456789012"` |
| `mpn` | string | no | MPN | `"GSX140361"` |
| `price` | number | yes | Price in dollars | `1299.00` |
| `currency` | string | yes | Currency code | `"USD"` |
| `availability` | string | yes | Normalized: IN_STOCK, OUT_OF_STOCK, PREORDER | `"IN_STOCK"` |
| `condition` | string | yes | Normalized: NEW, REFURBISHED, USED | `"NEW"` |
| `product_type` | string | no | Primary product type | `"HVAC > Air Conditioners"` |
| `custom_labels` | object | yes | Custom labels 0-4 | `{"0": "equipment"}` |
| `destinations` | object | yes | Destination eligibility | `{"Shopping_ads": "excluded"}` |
| `link` | string | yes | Product page URL | `"https://example.com/product"` |
| `image_link` | string | yes | Main image URL | `"https://example.com/image.jpg"` |

---

## Merchant Center — Product Statuses

### raw/merchant/product_statuses.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `extracted_at` | string | yes | ISO 8601 extraction timestamp | `"2026-01-15T14:30:52Z"` |
| `count` | number | yes | Number of records | `1763` |
| `records` | array | yes | Array of status objects | `[...]` |

#### Product Status Record

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `productId` | string | yes | Full product ID | `"online~en~US~SKU123"` |
| `destinationStatuses` | array | yes | Status per destination | `[...]` |
| `destinationStatuses[].destination` | string | yes | Destination name | `"Shopping_ads"` |
| `destinationStatuses[].status` | string | yes | Enum: approved, disapproved, pending | `"approved"` |
| `destinationStatuses[].disapprovedCountries` | array | no | Countries where disapproved | `[]` |
| `destinationStatuses[].pendingCountries` | array | no | Countries pending review | `[]` |
| `itemLevelIssues` | array | yes | Product-level issues | `[...]` |
| `itemLevelIssues[].code` | string | yes | Issue code | `"missing_gtin"` |
| `itemLevelIssues[].severity` | string | yes | Enum: critical, error, warning, info | `"warning"` |
| `itemLevelIssues[].description` | string | yes | Human-readable description | `"Missing GTIN"` |
| `itemLevelIssues[].applicableCountries` | array | yes | Affected countries | `["US"]` |

### normalized/merchant/issues.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `product_id` | string | yes | Full product ID | `"online~en~US~SKU123"` |
| `offer_id` | string | yes | Merchant's product ID | `"SKU123"` |
| `destination` | string | yes | Destination name | `"Shopping_ads"` |
| `status` | string | yes | Normalized: APPROVED, DISAPPROVED, PENDING, EXCLUDED | `"APPROVED"` |
| `issues` | array | yes | Array of issue objects | `[...]` |
| `issues[].code` | string | yes | Issue code | `"missing_gtin"` |
| `issues[].severity` | string | yes | Normalized: CRITICAL, ERROR, WARNING, INFO | `"WARNING"` |
| `issues[].description` | string | yes | Human-readable description | `"Missing GTIN"` |

---

## Enum Normalization Reference

### Status Values
| API Value | Normalized |
|-----------|------------|
| `ENABLED` | `ENABLED` |
| `PAUSED` | `PAUSED` |
| `REMOVED` | `REMOVED` |
| `approved` | `APPROVED` |
| `disapproved` | `DISAPPROVED` |
| `pending` | `PENDING` |

### Match Types
| API Value | Normalized |
|-----------|------------|
| `EXACT` | `EXACT` |
| `PHRASE` | `PHRASE` |
| `BROAD` | `BROAD` |

### Campaign Types
| API Value | Normalized |
|-----------|------------|
| `SEARCH` | `SEARCH` |
| `DISPLAY` | `DISPLAY` |
| `SHOPPING` | `SHOPPING` |
| `PERFORMANCE_MAX` | `PMAX` |
| `VIDEO` | `VIDEO` |

### Availability
| API Value | Normalized |
|-----------|------------|
| `in_stock` | `IN_STOCK` |
| `out_of_stock` | `OUT_OF_STOCK` |
| `preorder` | `PREORDER` |

### Quality Ratings
| API Value | Normalized |
|-----------|------------|
| `BELOW_AVERAGE` | `BELOW_AVERAGE` |
| `AVERAGE` | `AVERAGE` |
| `ABOVE_AVERAGE` | `ABOVE_AVERAGE` |
| `UNKNOWN` | `UNKNOWN` |

---

## Google Search Console

### raw/gsc/sites.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `extracted_at` | string | yes | ISO 8601 extraction timestamp | `"2026-01-15T14:30:52Z"` |
| `count` | number | yes | Number of verified sites | `1` |
| `records` | array | yes | Array of site objects | `[...]` |

#### Site Record

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `siteUrl` | string | yes | Verified site URL | `"https://buycomfortdirect.com/"` |
| `permissionLevel` | string | yes | Permission level | `"siteOwner"` |

### raw/gsc/search_analytics.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `extracted_at` | string | yes | ISO 8601 extraction timestamp | `"2026-01-15T14:30:52Z"` |
| `site_url` | string | yes | Site URL queried | `"https://buycomfortdirect.com"` |
| `date_range` | object | yes | Query date range | `{"start": "2025-12-16", "end": "2026-01-14"}` |
| `count` | number | yes | Number of rows | `15234` |
| `records` | array | yes | Array of analytics rows | `[...]` |
| `note` | string | no | Implementation note | `"Daily-level data with all dimensions"` |

#### Search Analytics Row

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `keys` | array | yes | Dimension values [query, page, device, country, date] | `["rheem furnace", "https://...", "MOBILE", "USA", "2026-01-14"]` |
| `clicks` | number | yes | Number of clicks | `12` |
| `impressions` | number | yes | Number of impressions | `456` |
| `ctr` | number | yes | Click-through rate | `0.0263` |
| `position` | number | yes | Average position | `8.3` |

### normalized/gsc/queries.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `count` | number | yes | Number of unique queries | `1234` |
| `records` | array | yes | Array of query objects | `[...]` |

#### Query Record

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `query` | string | yes | Search query text | `"rheem furnace"` |
| `clicks` | number | yes | Total clicks (aggregated) | `45` |
| `impressions` | number | yes | Total impressions (aggregated) | `2340` |
| `ctr` | number | yes | Overall CTR | `0.0192` |
| `position` | number | yes | Weighted average position | `7.2` |

### normalized/gsc/pages.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `count` | number | yes | Number of unique pages | `234` |
| `records` | array | yes | Array of page objects | `[...]` |

#### Page Record

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `page` | string | yes | Landing page URL | `"https://buycomfortdirect.com/product/rheem"` |
| `clicks` | number | yes | Total clicks (aggregated) | `123` |
| `impressions` | number | yes | Total impressions (aggregated) | `5678` |
| `ctr` | number | yes | Overall CTR | `0.0217` |
| `position` | number | yes | Weighted average position | `6.8` |

### normalized/gsc/summary.json

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `extracted_at` | string | yes | ISO 8601 extraction timestamp | `"2026-01-15T14:30:52Z"` |
| `site_url` | string | yes | Site URL | `"https://buycomfortdirect.com"` |
| `date_range` | object | yes | Date range | `{"start": "2025-12-16", "end": "2026-01-14"}` |
| `summary` | object | yes | Aggregate stats | `{...}` |
| `summary.total_clicks` | number | yes | Total clicks across all queries | `1234` |
| `summary.total_impressions` | number | yes | Total impressions | `45678` |
| `summary.avg_ctr` | number | yes | Overall CTR | `0.0270` |
| `summary.avg_position` | number | yes | Overall weighted average position | `7.5` |

**Note:** All GSC data is READ-ONLY. Position is weighted by impressions. CTR is calculated as clicks/impressions. No live API calls are made during query - all data comes from snapshots.
