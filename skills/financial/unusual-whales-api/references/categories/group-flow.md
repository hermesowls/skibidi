# group_flow

Source: https://api.unusualwhales.com/docs/openapi.yaml; retrieved 2026-09-24T01:21:27.462441+00:00

Full descriptions, inherited security, effective parameters, responses and schemas. No live calls.

## GET /api/group-flow/{flow_group}/greek-flow

Greek flow

Returns the group flow's greek flow (delta & vega flow) for the given market day broken down per minute.
Date must be the current or a past date. If no date is given, returns data for the current/last market day.


### Fully resolved operation
```json
{
  "key": "GET /api/group-flow/{flow_group}/greek-flow",
  "method": "GET",
  "path": "/api/group-flow/{flow_group}/greek-flow",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "Returns the group flow's greek flow (delta & vega flow) for the given market day broken down per minute.\nDate must be the current or a past date. If no date is given, returns data for the current/last market day.\n",
    "operationId": "PublicApi.GroupFlowController.greek_flow",
    "parameters": [
      {
        "description": "",
        "in": "path",
        "name": "flow_group",
        "required": true,
        "schema": {
          "description": "A flow group",
          "enum": [
            "airline",
            "bank",
            "basic materials",
            "china",
            "communication services",
            "consumer cyclical",
            "consumer defensive",
            "crypto",
            "cyber",
            "energy",
            "financial services",
            "gas",
            "gold",
            "healthcare",
            "industrials",
            "mag7",
            "oil",
            "real estate",
            "refiners",
            "reit",
            "semi",
            "silver",
            "technology",
            "uranium",
            "utilities"
          ],
          "example": "airline",
          "title": "SingleFlowGroup",
          "type": "string"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "date",
        "required": false,
        "schema": {
          "description": "A trading date in the format of YYYY-MM-DD.\nThis is optional and by default the last trading date.\n",
          "example": "2024-01-18",
          "title": "Optional Market Date",
          "type": "string"
        }
      }
    ],
    "responses": {
      "200": {
        "content": {
          "application/json": {
            "schema": {
              "description": "Greek flow by flow group and minute timestamps.",
              "example": {
                "data": [
                  {
                    "dir_delta_flow": "-43593.96",
                    "dir_vega_flow": "31243.04",
                    "flow_group": "airline",
                    "net_call_premium": "-1095135.00",
                    "net_call_volume": 1049,
                    "net_put_premium": "135732.00",
                    "net_put_volume": 415,
                    "otm_dir_delta_flow": "14947.51",
                    "otm_dir_vega_flow": "11421.03",
                    "otm_total_delta_flow": "-28564.02",
                    "otm_total_vega_flow": "101745.64",
                    "timestamp": "2024-10-28 18:46:00+00:00",
                    "total_delta_flow": "-21257.36",
                    "total_vega_flow": "350944.58",
                    "transactions": 1188,
                    "volume": 12348
                  }
                ]
              },
              "properties": {
                "dir_delta_flow": {
                  "description": "The directional delta flow.",
                  "example": "-43593.96",
                  "title": "Dir Delta Flow",
                  "type": "string"
                },
                "dir_vega_flow": {
                  "description": "The directional vega flow.",
                  "example": "31243.04",
                  "title": "Dir Vega Flow",
                  "type": "string"
                },
                "flow_group": {
                  "description": "A flow group where the flow data for all tickers in that group are aggregated.",
                  "enum": [
                    "airline",
                    "bank",
                    "basic materials",
                    "china",
                    "communication services",
                    "consumer cyclical",
                    "consumer defensive",
                    "crypto",
                    "cyber",
                    "energy",
                    "financial services",
                    "gas",
                    "gold",
                    "healthcare",
                    "industrials",
                    "mag7",
                    "oil",
                    "real estate",
                    "refiners",
                    "reit",
                    "semi",
                    "silver",
                    "technology",
                    "uranium",
                    "utilities"
                  ],
                  "example": "airline",
                  "title": "Flow Group",
                  "type": "string"
                },
                "net_call_premium": {
                  "description": "Defined as (call premium ask side) - (call premium bid side).",
                  "example": "-29138464",
                  "title": "Market General Net Call Premium",
                  "type": "string"
                },
                "net_call_volume": {
                  "description": "Defined as (call volume ask side) - (call volume bid side).",
                  "example": 1049,
                  "title": "Market General Net Call Volume",
                  "type": "integer"
                },
                "net_put_premium": {
                  "description": "Defined as (put premium ask side) - (put premium bid side).",
                  "example": "23924325",
                  "title": "Market General Net Put Premium",
                  "type": "string"
                },
                "net_put_volume": {
                  "description": "Defined as (put volume ask side) - (put volume bid side).",
                  "example": 1313,
                  "title": "Market General Net Put Volume",
                  "type": "integer"
                },
                "otm_dir_delta_flow": {
                  "description": "The directional delta flow of out-of-the-money options.",
                  "example": "14947.51",
                  "title": "OTM Dir Delta Flow",
                  "type": "string"
                },
                "otm_dir_vega_flow": {
                  "description": "The directional vega flow of out-of-the-money options.",
                  "example": "11421.03",
                  "title": "OTM Dir Vega Flow",
                  "type": "string"
                },
                "otm_total_delta_flow": {
                  "description": "The total delta flow of out-of-the-money options.",
                  "example": "-28564.02",
                  "title": "OTM Total Delta Flow",
                  "type": "string"
                },
                "otm_total_vega_flow": {
                  "description": "The total vega flow of out-of-the-money options.",
                  "example": "101745.64",
                  "title": "OTM Total Vega Flow",
                  "type": "string"
                },
                "timestamp": {
                  "description": "The (start of minute) timestamp of the data.",
                  "example": "2024-10-28 18:46:00+00:00",
                  "format": "date-time",
                  "title": "Timestamp",
                  "type": "string"
                },
                "total_delta_flow": {
                  "description": "The total delta flow.",
                  "example": "-21257.36",
                  "title": "Total Delta Flow",
                  "type": "string"
                },
                "total_vega_flow": {
                  "description": "The total vega flow.",
                  "example": "350944.58",
                  "title": "Total Vega Flow",
                  "type": "string"
                },
                "transactions": {
                  "description": "The amount of transactions.",
                  "example": 1188,
                  "title": "Transactions",
                  "type": "integer"
                },
                "volume": {
                  "description": "The total options volume.",
                  "example": 12348,
                  "title": "Volume",
                  "type": "integer"
                }
              },
              "title": "Group Flow",
              "type": "object"
            }
          }
        },
        "description": ""
      },
      "401": {
        "content": {
          "application/json": {
            "schema": {
              "description": "Returned with HTTP 401 when a request carries no API token, or carries one the API cannot use. The response also carries a `WWW-Authenticate` header with the `Bearer` challenge. Branch on `reason` rather than on `message`, whose wording can change.",
              "example": {
                "code": "authentication_required",
                "documentation_url": "https://api.unusualwhales.com/docs",
                "expected_format": "uuid",
                "message": "The API token provided is not in the expected format. Unusual Whales API tokens are UUIDs, such as 123e4567-e89b-12d3-a456-426614174000.",
                "reason": "malformed_token",
                "request_id": "GNI_YTC1CRnw2LACGBvE",
                "retryable": false,
                "support_email": "dev@unusualwhales.com",
                "token_url": "https://unusualwhales.com/dashboard/api"
              },
              "properties": {
                "code": {
                  "description": "Always `authentication_required`.",
                  "enum": [
                    "authentication_required"
                  ],
                  "type": "string"
                },
                "documentation_url": {
                  "description": "Where to read this API documentation.",
                  "type": "string"
                },
                "expected_format": {
                  "description": "Present only when `reason` is `malformed_token`. The format the token must take.",
                  "enum": [
                    "uuid"
                  ],
                  "type": "string"
                },
                "message": {
                  "description": "A plain description of the failure, written for a person.",
                  "type": "string"
                },
                "reason": {
                  "description": "Which authentication failure occurred. `missing_token` means the request carried no token. `malformed_token` means a token was supplied but is not a UUID. `unrecognized_token` means the token is a UUID that no active token matches, which happens after a token is revoked or regenerated, or when it belongs to a different account.",
                  "enum": [
                    "missing_token",
                    "malformed_token",
                    "unrecognized_token"
                  ],
                  "type": "string"
                },
                "request_id": {
                  "description": "Identifies this request in Unusual Whales logs. Quote it when contacting support. It matches the `x-request-id` response header, and is absent when no request id was assigned.",
                  "type": "string"
                },
                "retryable": {
                  "description": "Always `false`. Replaying the same request unchanged returns the same error. Retrying with a corrected token can succeed.",
                  "enum": [
                    false
                  ],
                  "type": "boolean"
                },
                "support_email": {
                  "description": "Where to send questions about API access.",
                  "type": "string"
                },
                "token_url": {
                  "description": "Where to create and manage API tokens.",
                  "type": "string"
                }
              },
              "title": "Authentication Error",
              "type": "object"
            }
          }
        },
        "description": "Unauthorized"
      },
      "403": {
        "content": {
          "application/json": {
            "schema": {
              "description": "Returned with HTTP 403 when the API token is valid and recognized, but is not entitled to what the request asked for. Branch on `code`, which names the entitlement that is missing; `message` is written for a person and its wording can change. Unlike a 401 this response carries no `WWW-Authenticate` header, because presenting different credentials for the same token does not change the outcome.\n\nOnly `code` and `message` are guaranteed. The remaining fields are sent by some checks and not others, so treat every one of them as optional.\n\nA 403 whose body is not JSON, or is JSON without a `code` field, did not come from this API. Those are produced by Cloudflare in front of the API, or by a proxy on the caller's own network, and neither says anything about the token or the subscription.",
              "example": {
                "code": "missing_access",
                "documentation_url": "https://api.unusualwhales.com/docs",
                "message": "The API token provided is valid but is not permitted to access this route.",
                "reason": "route_not_permitted",
                "request_id": "GNI_YTC1CRnw2LACGBvE",
                "retryable": false,
                "support_email": "dev@unusualwhales.com",
                "token_url": "https://unusualwhales.com/dashboard/api"
              },
              "properties": {
                "code": {
                  "description": "Which entitlement is missing. `missing_access` means the token is restricted to a set of routes that excludes the requested one. `historic_data_access_missing` means a date in the request predates the earliest date the token may query. `advanced_tier_required`, `futures_access_required`, `politics_scope_required` and `volatility_scope_required` each mean the endpoint needs a subscription tier or data add-on the account does not have. `admin_required` means the endpoint is internal to Unusual Whales.",
                  "enum": [
                    "missing_access",
                    "historic_data_access_missing",
                    "advanced_tier_required",
                    "futures_access_required",
                    "politics_scope_required",
                    "volatility_scope_required",
                    "admin_required"
                  ],
                  "type": "string"
                },
                "documentation_url": {
                  "description": "Where to read this API documentation.",
                  "type": "string"
                },
                "message": {
                  "description": "A plain description of what is missing and how to obtain it, written for a person. Do not branch on this string.",
                  "type": "string"
                },
                "reason": {
                  "description": "Present only when `code` is `missing_access`. Narrows the cause within that code.",
                  "enum": [
                    "route_not_permitted"
                  ],
                  "type": "string"
                },
                "request_id": {
                  "description": "Identifies this request in Unusual Whales logs. Quote it when contacting support. It matches the `x-request-id` response header, and is absent when no request id was assigned.",
                  "type": "string"
                },
                "retryable": {
                  "description": "When present, always `false`. Replaying the same request unchanged returns the same error. Changing the request, the token, or the subscription can succeed.",
                  "enum": [
                    false
                  ],
                  "type": "boolean"
                },
                "support_email": {
                  "description": "Where to send questions about API access.",
                  "type": "string"
                },
                "token_url": {
                  "description": "Where to create and manage API tokens.",
                  "type": "string"
                }
              },
              "required": [
                "code",
                "message"
              ],
              "title": "Forbidden Error",
              "type": "object"
            }
          }
        },
        "description": "Forbidden"
      }
    },
    "summary": "Greek flow",
    "tags": [
      "group_flow"
    ],
    "security": [
      {
        "authorization": []
      }
    ],
    "servers": [
      {
        "url": "https://api.unusualwhales.com",
        "variables": {}
      }
    ]
  }
}

```

## GET /api/group-flow/{flow_group}/greek-flow/{expiry}

Greek flow by expiry

Returns the group flow's greek flow (delta & vega flow) for the given market day broken down per minute & expiry.
Date must be the current or a past date. If no date is given, returns data for the current/last market day.


### Fully resolved operation
```json
{
  "key": "GET /api/group-flow/{flow_group}/greek-flow/{expiry}",
  "method": "GET",
  "path": "/api/group-flow/{flow_group}/greek-flow/{expiry}",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "Returns the group flow's greek flow (delta & vega flow) for the given market day broken down per minute & expiry.\nDate must be the current or a past date. If no date is given, returns data for the current/last market day.\n",
    "operationId": "PublicApi.GroupFlowController.greek_flow_expiry",
    "parameters": [
      {
        "description": "",
        "in": "path",
        "name": "flow_group",
        "required": true,
        "schema": {
          "description": "A flow group",
          "enum": [
            "airline",
            "bank",
            "basic materials",
            "china",
            "communication services",
            "consumer cyclical",
            "consumer defensive",
            "crypto",
            "cyber",
            "energy",
            "financial services",
            "gas",
            "gold",
            "healthcare",
            "industrials",
            "mag7",
            "oil",
            "real estate",
            "refiners",
            "reit",
            "semi",
            "silver",
            "technology",
            "uranium",
            "utilities"
          ],
          "example": "airline",
          "title": "SingleFlowGroup",
          "type": "string"
        }
      },
      {
        "description": "",
        "in": "path",
        "name": "expiry",
        "required": true,
        "schema": {
          "description": "A single expiry date in ISO date format.",
          "example": "2024-02-02",
          "title": "Single expiry date",
          "type": "string"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "date",
        "required": false,
        "schema": {
          "description": "A trading date in the format of YYYY-MM-DD.\nThis is optional and by default the last trading date.\n",
          "example": "2024-01-18",
          "title": "Optional Market Date",
          "type": "string"
        }
      }
    ],
    "responses": {
      "200": {
        "content": {
          "application/json": {
            "schema": {
              "description": "Greek flow by flow group, minute timestamps, and expiry date.",
              "example": {
                "data": [
                  {
                    "dir_delta_flow": "-43593.96",
                    "dir_vega_flow": "31243.04",
                    "expiry": "2024-10-28",
                    "flow_group": "airline",
                    "net_call_premium": "-1095135.00",
                    "net_call_volume": 1049,
                    "net_put_premium": "135732.00",
                    "net_put_volume": 415,
                    "otm_dir_delta_flow": "14947.51",
                    "otm_dir_vega_flow": "11421.03",
                    "otm_total_delta_flow": "-28564.02",
                    "otm_total_vega_flow": "101745.64",
                    "timestamp": "2024-10-28 18:46:00+00:00",
                    "total_delta_flow": "-21257.36",
                    "total_vega_flow": "350944.58",
                    "transactions": 1188,
                    "volume": 12348
                  }
                ]
              },
              "properties": {
                "dir_delta_flow": {
                  "description": "The directional delta flow.",
                  "example": "-43593.96",
                  "title": "Dir Delta Flow",
                  "type": "string"
                },
                "dir_vega_flow": {
                  "description": "The directional vega flow.",
                  "example": "31243.04",
                  "title": "Dir Vega Flow",
                  "type": "string"
                },
                "expiry": {
                  "description": "The contract expiry date in ISO format.",
                  "example": "2023-12-22",
                  "title": "Option Contract Expiry",
                  "type": "string"
                },
                "flow_group": {
                  "description": "A flow group where the flow data for all tickers in that group are aggregated.",
                  "enum": [
                    "airline",
                    "bank",
                    "basic materials",
                    "china",
                    "communication services",
                    "consumer cyclical",
                    "consumer defensive",
                    "crypto",
                    "cyber",
                    "energy",
                    "financial services",
                    "gas",
                    "gold",
                    "healthcare",
                    "industrials",
                    "mag7",
                    "oil",
                    "real estate",
                    "refiners",
                    "reit",
                    "semi",
                    "silver",
                    "technology",
                    "uranium",
                    "utilities"
                  ],
                  "example": "airline",
                  "title": "Flow Group",
                  "type": "string"
                },
                "net_call_premium": {
                  "description": "Defined as (call premium ask side) - (call premium bid side).",
                  "example": "-29138464",
                  "title": "Market General Net Call Premium",
                  "type": "string"
                },
                "net_call_volume": {
                  "description": "Defined as (call volume ask side) - (call volume bid side).",
                  "example": 1049,
                  "title": "Market General Net Call Volume",
                  "type": "integer"
                },
                "net_put_premium": {
                  "description": "Defined as (put premium ask side) - (put premium bid side).",
                  "example": "23924325",
                  "title": "Market General Net Put Premium",
                  "type": "string"
                },
                "net_put_volume": {
                  "description": "Defined as (put volume ask side) - (put volume bid side).",
                  "example": 1313,
                  "title": "Market General Net Put Volume",
                  "type": "integer"
                },
                "otm_dir_delta_flow": {
                  "description": "The directional delta flow of out-of-the-money options.",
                  "example": "14947.51",
                  "title": "OTM Dir Delta Flow",
                  "type": "string"
                },
                "otm_dir_vega_flow": {
                  "description": "The directional vega flow of out-of-the-money options.",
                  "example": "11421.03",
                  "title": "OTM Dir Vega Flow",
                  "type": "string"
                },
                "otm_total_delta_flow": {
                  "description": "The total delta flow of out-of-the-money options.",
                  "example": "-28564.02",
                  "title": "OTM Total Delta Flow",
                  "type": "string"
                },
                "otm_total_vega_flow": {
                  "description": "The total vega flow of out-of-the-money options.",
                  "example": "101745.64",
                  "title": "OTM Total Vega Flow",
                  "type": "string"
                },
                "timestamp": {
                  "description": "The (start of minute) timestamp of the data.",
                  "example": "2024-10-28 18:46:00+00:00",
                  "format": "date-time",
                  "title": "Timestamp",
                  "type": "string"
                },
                "total_delta_flow": {
                  "description": "The total delta flow.",
                  "example": "-21257.36",
                  "title": "Total Delta Flow",
                  "type": "string"
                },
                "total_vega_flow": {
                  "description": "The total vega flow.",
                  "example": "350944.58",
                  "title": "Total Vega Flow",
                  "type": "string"
                },
                "transactions": {
                  "description": "The amount of transactions.",
                  "example": 1188,
                  "title": "Transactions",
                  "type": "integer"
                },
                "volume": {
                  "description": "The total options volume.",
                  "example": 12348,
                  "title": "Volume",
                  "type": "integer"
                }
              },
              "title": "Group Flow Expiry",
              "type": "object"
            }
          }
        },
        "description": ""
      },
      "401": {
        "content": {
          "application/json": {
            "schema": {
              "description": "Returned with HTTP 401 when a request carries no API token, or carries one the API cannot use. The response also carries a `WWW-Authenticate` header with the `Bearer` challenge. Branch on `reason` rather than on `message`, whose wording can change.",
              "example": {
                "code": "authentication_required",
                "documentation_url": "https://api.unusualwhales.com/docs",
                "expected_format": "uuid",
                "message": "The API token provided is not in the expected format. Unusual Whales API tokens are UUIDs, such as 123e4567-e89b-12d3-a456-426614174000.",
                "reason": "malformed_token",
                "request_id": "GNI_YTC1CRnw2LACGBvE",
                "retryable": false,
                "support_email": "dev@unusualwhales.com",
                "token_url": "https://unusualwhales.com/dashboard/api"
              },
              "properties": {
                "code": {
                  "description": "Always `authentication_required`.",
                  "enum": [
                    "authentication_required"
                  ],
                  "type": "string"
                },
                "documentation_url": {
                  "description": "Where to read this API documentation.",
                  "type": "string"
                },
                "expected_format": {
                  "description": "Present only when `reason` is `malformed_token`. The format the token must take.",
                  "enum": [
                    "uuid"
                  ],
                  "type": "string"
                },
                "message": {
                  "description": "A plain description of the failure, written for a person.",
                  "type": "string"
                },
                "reason": {
                  "description": "Which authentication failure occurred. `missing_token` means the request carried no token. `malformed_token` means a token was supplied but is not a UUID. `unrecognized_token` means the token is a UUID that no active token matches, which happens after a token is revoked or regenerated, or when it belongs to a different account.",
                  "enum": [
                    "missing_token",
                    "malformed_token",
                    "unrecognized_token"
                  ],
                  "type": "string"
                },
                "request_id": {
                  "description": "Identifies this request in Unusual Whales logs. Quote it when contacting support. It matches the `x-request-id` response header, and is absent when no request id was assigned.",
                  "type": "string"
                },
                "retryable": {
                  "description": "Always `false`. Replaying the same request unchanged returns the same error. Retrying with a corrected token can succeed.",
                  "enum": [
                    false
                  ],
                  "type": "boolean"
                },
                "support_email": {
                  "description": "Where to send questions about API access.",
                  "type": "string"
                },
                "token_url": {
                  "description": "Where to create and manage API tokens.",
                  "type": "string"
                }
              },
              "title": "Authentication Error",
              "type": "object"
            }
          }
        },
        "description": "Unauthorized"
      },
      "403": {
        "content": {
          "application/json": {
            "schema": {
              "description": "Returned with HTTP 403 when the API token is valid and recognized, but is not entitled to what the request asked for. Branch on `code`, which names the entitlement that is missing; `message` is written for a person and its wording can change. Unlike a 401 this response carries no `WWW-Authenticate` header, because presenting different credentials for the same token does not change the outcome.\n\nOnly `code` and `message` are guaranteed. The remaining fields are sent by some checks and not others, so treat every one of them as optional.\n\nA 403 whose body is not JSON, or is JSON without a `code` field, did not come from this API. Those are produced by Cloudflare in front of the API, or by a proxy on the caller's own network, and neither says anything about the token or the subscription.",
              "example": {
                "code": "missing_access",
                "documentation_url": "https://api.unusualwhales.com/docs",
                "message": "The API token provided is valid but is not permitted to access this route.",
                "reason": "route_not_permitted",
                "request_id": "GNI_YTC1CRnw2LACGBvE",
                "retryable": false,
                "support_email": "dev@unusualwhales.com",
                "token_url": "https://unusualwhales.com/dashboard/api"
              },
              "properties": {
                "code": {
                  "description": "Which entitlement is missing. `missing_access` means the token is restricted to a set of routes that excludes the requested one. `historic_data_access_missing` means a date in the request predates the earliest date the token may query. `advanced_tier_required`, `futures_access_required`, `politics_scope_required` and `volatility_scope_required` each mean the endpoint needs a subscription tier or data add-on the account does not have. `admin_required` means the endpoint is internal to Unusual Whales.",
                  "enum": [
                    "missing_access",
                    "historic_data_access_missing",
                    "advanced_tier_required",
                    "futures_access_required",
                    "politics_scope_required",
                    "volatility_scope_required",
                    "admin_required"
                  ],
                  "type": "string"
                },
                "documentation_url": {
                  "description": "Where to read this API documentation.",
                  "type": "string"
                },
                "message": {
                  "description": "A plain description of what is missing and how to obtain it, written for a person. Do not branch on this string.",
                  "type": "string"
                },
                "reason": {
                  "description": "Present only when `code` is `missing_access`. Narrows the cause within that code.",
                  "enum": [
                    "route_not_permitted"
                  ],
                  "type": "string"
                },
                "request_id": {
                  "description": "Identifies this request in Unusual Whales logs. Quote it when contacting support. It matches the `x-request-id` response header, and is absent when no request id was assigned.",
                  "type": "string"
                },
                "retryable": {
                  "description": "When present, always `false`. Replaying the same request unchanged returns the same error. Changing the request, the token, or the subscription can succeed.",
                  "enum": [
                    false
                  ],
                  "type": "boolean"
                },
                "support_email": {
                  "description": "Where to send questions about API access.",
                  "type": "string"
                },
                "token_url": {
                  "description": "Where to create and manage API tokens.",
                  "type": "string"
                }
              },
              "required": [
                "code",
                "message"
              ],
              "title": "Forbidden Error",
              "type": "object"
            }
          }
        },
        "description": "Forbidden"
      }
    },
    "summary": "Greek flow by expiry",
    "tags": [
      "group_flow"
    ],
    "security": [
      {
        "authorization": []
      }
    ],
    "servers": [
      {
        "url": "https://api.unusualwhales.com",
        "variables": {}
      }
    ]
  }
}

```
