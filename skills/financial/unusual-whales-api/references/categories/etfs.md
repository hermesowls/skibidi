# etfs

Source: https://api.unusualwhales.com/docs/openapi.yaml; retrieved 2026-09-24T01:21:27.462441+00:00

Full descriptions, inherited security, effective parameters, responses and schemas. No live calls.

## GET /api/etfs/{ticker}/exposure

Exposure

Returns all ETFs in which the given ticker is a holding


### Fully resolved operation
```json
{
  "key": "GET /api/etfs/{ticker}/exposure",
  "method": "GET",
  "path": "/api/etfs/{ticker}/exposure",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "Returns all ETFs in which the given ticker is a holding\n",
    "operationId": "PublicApi.EtfController.exposure",
    "parameters": [
      {
        "description": "",
        "in": "path",
        "name": "ticker",
        "required": true,
        "schema": {
          "description": "A single ticker",
          "example": "AAPL",
          "title": "SingleTicker",
          "type": "string"
        }
      }
    ],
    "responses": {
      "200": {
        "content": {
          "application/json": {
            "schema": {
              "description": "Returns the ETFs in which the given ticker is a holding\n",
              "example": {
                "data": [
                  {
                    "etf": "VTI",
                    "full_name": "VANGUARD TOTAL STOCK MARKET INDEX FUND",
                    "last_price": "236.16",
                    "prev_price": "235.25",
                    "shares": 130464268,
                    "weight": "0.35"
                  },
                  {
                    "etf": "VOO",
                    "full_name": "VANGUARD 500 INDEX FUND",
                    "last_price": "435.2",
                    "prev_price": "433.19",
                    "shares": 102076425,
                    "weight": "0.49"
                  },
                  {
                    "etf": "QQQ",
                    "full_name": "INVESCO QQQ",
                    "last_price": "405.97",
                    "prev_price": "404.96",
                    "shares": 75412427,
                    "weight": "1.566"
                  },
                  {
                    "etf": "SPY",
                    "full_name": "SPDR S&P 500 ETF",
                    "last_price": "471.55",
                    "prev_price": "469.37",
                    "shares": 48427939,
                    "weight": "0.476355"
                  }
                ]
              },
              "properties": {
                "etf": {
                  "description": "The ticker of the ETF.",
                  "example": "VTI",
                  "title": "Etf Ticker",
                  "type": "string"
                },
                "full_name": {
                  "description": "The full name of the ETF.",
                  "example": "SPDR S&P 500 ETF Trust",
                  "title": "Etf Full Name",
                  "type": "string"
                },
                "last_price": {
                  "description": "The closing price of the candle.",
                  "example": "56.79",
                  "title": "Candle Close",
                  "type": "string"
                },
                "prev_price": {
                  "description": "The previous trading day's stock price of the ticker.",
                  "example": "189.70",
                  "title": "Stock Prev Close Price",
                  "type": "string"
                },
                "shares": {
                  "description": "The amount of shares that the ETF holds.",
                  "example": 48427939,
                  "title": "Etf Shares",
                  "type": "integer"
                },
                "weight": {
                  "description": "The weight in percentage that the position represents in the ETF.",
                  "example": "0.35",
                  "title": "Etf Weight",
                  "type": "string"
                }
              },
              "title": "Exposure",
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
    "summary": "Exposure",
    "tags": [
      "etfs"
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

## GET /api/etfs/{ticker}/holdings

Holdings

Returns the holdings of the ETF


### Fully resolved operation
```json
{
  "key": "GET /api/etfs/{ticker}/holdings",
  "method": "GET",
  "path": "/api/etfs/{ticker}/holdings",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "Returns the holdings of the ETF\n",
    "operationId": "PublicApi.EtfController.holdings",
    "parameters": [
      {
        "description": "",
        "in": "path",
        "name": "ticker",
        "required": true,
        "schema": {
          "description": "A single ticker",
          "example": "AAPL",
          "title": "SingleTicker",
          "type": "string"
        }
      }
    ],
    "responses": {
      "200": {
        "content": {
          "application/json": {
            "schema": {
              "description": "",
              "example": {
                "data": [
                  {
                    "avg30_volume": "52433648",
                    "bearish_premium": "32565174",
                    "bullish_premium": "22987045",
                    "call_premium": "45254976",
                    "call_volume": 197685,
                    "close": "194.84",
                    "has_options": true,
                    "high": "196.579",
                    "low": "194.41",
                    "name": "APPLE INC",
                    "prev_price": "197.14",
                    "put_premium": "16338631",
                    "put_volume": 106773,
                    "sector": "Technology",
                    "shares": 169938760,
                    "short_name": "APPLE",
                    "ticker": "AAPL",
                    "type": "stock",
                    "volume": 12314310,
                    "week52_high": "199.62",
                    "week52_low": "123.15",
                    "weight": "7.335"
                  },
                  {
                    "avg30_volume": "30239291",
                    "bearish_premium": "14318236",
                    "bullish_premium": "14142305",
                    "call_premium": "22499010",
                    "call_volume": 48302,
                    "close": "371.0",
                    "has_options": true,
                    "high": "371.0",
                    "low": "368.73",
                    "name": "MICROSOFT CORP",
                    "prev_price": "369.36",
                    "put_premium": "8688334",
                    "put_volume": 35055,
                    "sector": "Technology",
                    "shares": 85913823,
                    "short_name": "MICROSOFT",
                    "ticker": "MSFT",
                    "type": "stock",
                    "volume": 3760724,
                    "week52_high": "384.3",
                    "week52_low": "216.98",
                    "weight": "6.959"
                  },
                  {
                    "avg30_volume": "51068229",
                    "bearish_premium": "27305757",
                    "bullish_premium": "37477652",
                    "call_premium": "68914858",
                    "call_volume": 243442,
                    "close": "152.82",
                    "has_options": true,
                    "high": "152.9",
                    "low": "150.09",
                    "name": "AMAZON.COM INC",
                    "prev_price": "149.6",
                    "put_premium": "15242490",
                    "put_volume": 86301,
                    "sector": "Consumer Cyclical",
                    "shares": 104991822,
                    "short_name": "AMAZON",
                    "ticker": "AMZN",
                    "type": "stock",
                    "volume": 11285233,
                    "week52_high": "150.57",
                    "week52_low": "81.43",
                    "weight": "3.44"
                  }
                ]
              },
              "properties": {
                "avg30_volume": {
                  "description": "The avg stock volume for the stock last 30 days.",
                  "example": "55973002",
                  "title": "Stock Average 30 Day Volume",
                  "type": "string"
                },
                "bearish_premium": {
                  "description": "The bearish premium is defined as (call premium bid side) + (put premium ask side).",
                  "example": "143198625",
                  "title": "Market General Bearish Premium",
                  "type": "string"
                },
                "bullish_premium": {
                  "description": "The bullish premium is defined as (call premium ask side) + (put premium bid side).",
                  "example": "196261414",
                  "title": "Market General Bullish Premium",
                  "type": "string"
                },
                "call_premium": {
                  "description": "The sum of the premium of all the call transactions that executed.",
                  "example": "9908777.0",
                  "title": "Market General Call Premium",
                  "type": "string"
                },
                "call_volume": {
                  "description": "The sum of the size of all the call transactions that executed.",
                  "example": 990943,
                  "title": "Market General Call Volume",
                  "type": "integer"
                },
                "close": {
                  "description": "The closing price of the candle.",
                  "example": "56.79",
                  "title": "Candle Close",
                  "type": "string"
                },
                "has_options": {
                  "description": "Boolean flag whether the company has options.",
                  "example": true,
                  "title": "Stock Has Options",
                  "type": "boolean"
                },
                "high": {
                  "description": "The highest price of the candle.",
                  "example": "58.12",
                  "title": "Candle High",
                  "type": "string"
                },
                "low": {
                  "description": "The lowest price of the candle.",
                  "example": "51.90",
                  "title": "Candle Low",
                  "type": "string"
                },
                "name": {
                  "description": "The name of the company.",
                  "example": "APPLE INC",
                  "title": "Stock Company Name",
                  "type": "string"
                },
                "open": {
                  "description": "The opening price of the candle.",
                  "example": "54.29",
                  "title": "Candle Open",
                  "type": "string"
                },
                "prev_price": {
                  "description": "The previous trading day's stock price of the ticker.",
                  "example": "189.70",
                  "title": "Stock Prev Close Price",
                  "type": "string"
                },
                "put_premium": {
                  "description": "The sum of the premium of all the put transactions that executed.",
                  "example": "163537151",
                  "title": "Market General Put Premium",
                  "type": "string"
                },
                "put_volume": {
                  "description": "The sum of the size of all the put transactions that executed.",
                  "example": 808326,
                  "title": "Market General Put Volume",
                  "type": "integer"
                },
                "sector": {
                  "description": "The financial sector of the ticker. Empty if unknown or not applicable such as ETF/Index.",
                  "enum": [
                    "Basic Materials",
                    "Communication Services",
                    "Consumer Cyclical",
                    "Consumer Defensive",
                    "Energy",
                    "Financial Services",
                    "Healthcare",
                    "Industrials",
                    "Real Estate",
                    "Technology",
                    "Utilities"
                  ],
                  "example": "Technology",
                  "title": "Market General Sector",
                  "type": "string"
                },
                "ticker": {
                  "description": "The stock ticker.",
                  "example": "AAPL",
                  "title": "Stock Ticker",
                  "type": "string"
                },
                "volume": {
                  "description": "The volume of the ticker for the trading day.",
                  "example": 23132119,
                  "title": "Stock Day Stock Volume",
                  "type": "integer"
                },
                "week_52_high": {
                  "description": "The 52 week high stock price of the ticker.",
                  "example": "198.23",
                  "title": "Stock Week 52 High",
                  "type": "string"
                },
                "week_52_low": {
                  "description": "The 52 week low stock price of the ticker.",
                  "example": "124.17",
                  "title": "Stock Week 52 low",
                  "type": "string"
                }
              },
              "title": "Holdings",
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
    "summary": "Holdings",
    "tags": [
      "etfs"
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

## GET /api/etfs/{ticker}/in-outflow

Inflow & Outflow

Returns an ETF's inflow and outflow.
Defaults to the last year of data. Maximum date range is 3 years.


### Fully resolved operation
```json
{
  "key": "GET /api/etfs/{ticker}/in-outflow",
  "method": "GET",
  "path": "/api/etfs/{ticker}/in-outflow",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "Returns an ETF's inflow and outflow.\nDefaults to the last year of data. Maximum date range is 3 years.\n",
    "operationId": "PublicApi.EtfController.in_outflow",
    "parameters": [
      {
        "description": "",
        "in": "path",
        "name": "ticker",
        "required": true,
        "schema": {
          "description": "A single ticker",
          "example": "AAPL",
          "title": "SingleTicker",
          "type": "string"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "start_date",
        "required": false,
        "schema": {
          "description": "A trading date in the format of YYYY-MM-DD.\nThis is optional and by default the last trading date.\n",
          "example": "2024-01-18",
          "title": "Optional Market Date",
          "type": "string"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "end_date",
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
              "description": "",
              "example": {
                "data": [
                  {
                    "change": -50,
                    "change_prem": "-12000.0",
                    "close": "236.16",
                    "date": "2024-10-02",
                    "is_fomc": false,
                    "volume": 592342
                  },
                  {
                    "change": 100,
                    "change_prem": "23500.0",
                    "close": "235.12",
                    "date": "2024-10-01",
                    "is_fomc": false,
                    "volume": 602342
                  }
                ]
              },
              "properties": {
                "change": {
                  "description": "The net in/outflow measured as volume.",
                  "example": -50,
                  "title": "Etf Share Change",
                  "type": "integer"
                },
                "change_prem": {
                  "description": "The net in/outflow measured as premium.",
                  "example": "-5023.50",
                  "title": "Etf Premium Change",
                  "type": "string"
                },
                "close": {
                  "description": "The close stock price of the ticker.",
                  "example": "182.91",
                  "title": "Stock Close Price",
                  "type": "string"
                },
                "date": {
                  "description": "An ISO date.",
                  "example": "2024-01-09",
                  "title": "General ISO Date",
                  "type": "string"
                },
                "is_fomc": {
                  "description": "If the date has an FOMC announcement.",
                  "example": false,
                  "title": "Is FOMC Date",
                  "type": "boolean"
                },
                "volume": {
                  "description": "The volume of the ticker for the trading day.",
                  "example": 23132119,
                  "title": "Stock Day Stock Volume",
                  "type": "integer"
                }
              },
              "title": "Inflow & Outflow",
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
    "summary": "Inflow & Outflow",
    "tags": [
      "etfs"
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

## GET /api/etfs/{ticker}/info

Information

Returns the information about the given ETF ticker.


### Fully resolved operation
```json
{
  "key": "GET /api/etfs/{ticker}/info",
  "method": "GET",
  "path": "/api/etfs/{ticker}/info",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "Returns the information about the given ETF ticker.\n",
    "operationId": "PublicApi.EtfController.info",
    "parameters": [
      {
        "description": "",
        "in": "path",
        "name": "ticker",
        "required": true,
        "schema": {
          "description": "A single ticker",
          "example": "AAPL",
          "title": "SingleTicker",
          "type": "string"
        }
      }
    ],
    "responses": {
      "200": {
        "content": {
          "application/json": {
            "schema": {
              "description": "",
              "example": {
                "data": {
                  "aum": "428887833900",
                  "avg30_volume": "73784934",
                  "call_vol": 284364,
                  "description": "The Trust seeks to achieve its investment objective by holding a portfolio of the common stocks that are included in the index (the “Portfolio”), with the weight of each stock in the Portfolio substantially corresponding to the weight of such stock in the index.",
                  "domicile": "US",
                  "etf_company": "SPDR",
                  "expense_ratio": "0.0945",
                  "has_options": true,
                  "holdings_count": 503,
                  "inception_date": "1993-01-22",
                  "name": "SPDR S&P 500 ETF Trust",
                  "opt_vol": 533227,
                  "put_vol": 248863,
                  "stock_vol": 4348819,
                  "website": "https://www.ssga.com/us/en/institutional/etfs/funds/spdr-sp-500-etf-trust-spy"
                }
              },
              "properties": {
                "aum": {
                  "description": "The total assets under management (AUM) of the ETF.",
                  "example": "428887833900",
                  "title": "Etf AUM",
                  "type": "string"
                },
                "avg30_volume": {
                  "description": "The avg stock volume for the stock last 30 days.",
                  "example": "55973002",
                  "title": "Stock Average 30 Day Volume",
                  "type": "string"
                },
                "call_vol": {
                  "description": "The sum of the size of all the call transactions that executed.",
                  "example": 990943,
                  "title": "Market General Call Volume",
                  "type": "integer"
                },
                "description": {
                  "description": "Information about the ETF.",
                  "example": "The Trust seeks to achieve its investment objective by holding a portfolio of the common stocks that are included in the index (the “Portfolio”), with the weight of each stock in the Portfolio substantially corresponding to the weight of such stock in the index.",
                  "title": "Etf Description",
                  "type": "string"
                },
                "domicile": {
                  "description": "The domicile of the ETF.",
                  "example": "US",
                  "title": "Etf Domicile",
                  "type": "string"
                },
                "etf_company": {
                  "description": "The company which oversees the ETF.",
                  "example": "SPDR",
                  "title": "Etf Company",
                  "type": "string"
                },
                "expense_ratio": {
                  "description": "The expense ratio of the ETF.",
                  "example": "0.0945",
                  "title": "Etf Expense Ratio",
                  "type": "string"
                },
                "has_options": {
                  "description": "Boolean flag whether the company has options.",
                  "example": true,
                  "title": "Stock Has Options",
                  "type": "boolean"
                },
                "holdings_count": {
                  "description": "The amount of holdings the ETF has.",
                  "example": 503,
                  "title": "Etf Holdings Count",
                  "type": "integer"
                },
                "inception_date": {
                  "description": "The inception date of the ETF as an ISO date.",
                  "example": "1993-01-22",
                  "title": "Etf Inception Date",
                  "type": "string"
                },
                "name": {
                  "description": "The full name of the ETF.",
                  "example": "SPDR S&P 500 ETF Trust",
                  "title": "Etf Full Name",
                  "type": "string"
                },
                "opt_vol": {
                  "description": "The total options volume traded for the last trading day.",
                  "example": 533227,
                  "title": "Etf Total Volume",
                  "type": "integer"
                },
                "put_vol": {
                  "description": "The sum of the size of all the put transactions that executed.",
                  "example": 808326,
                  "title": "Market General Put Volume",
                  "type": "integer"
                },
                "stock_vol": {
                  "description": "The volume of the ticker for the trading day.",
                  "example": 23132119,
                  "title": "Stock Day Stock Volume",
                  "type": "integer"
                },
                "website": {
                  "description": "A link to the website of the ETF.",
                  "example": "https://www.ssga.com/us/en/institutional/etfs/funds/spdr-sp-500-etf-trust-spy",
                  "title": "Etf Website Url",
                  "type": "string"
                }
              },
              "title": "Etf Info",
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
      },
      "422": {
        "content": {
          "application/json": {
            "schema": {
              "description": "A json object containing information on the error cause.",
              "example": {
                "msg": "Invalid path input: MSFT12 (valid example: AAPL) - Invalid query input(s): date=2023-02-140 (valid example: date=2024-01-18)",
                "path": "/api/darkpool/MSFT12",
                "query": "date=2023-02-140",
                "url": "localhost:4000/api/darkpool/MSFT12?date=2023-02-140"
              },
              "properties": {
                "msg": {
                  "description": "An error message containing information about the faulty input.",
                  "type": "string"
                },
                "path": {
                  "description": "The URL path segment.",
                  "type": "string"
                },
                "query": {
                  "description": "The URL query segment.",
                  "type": "string"
                },
                "url": {
                  "description": "The full URL causing the error.",
                  "type": "string"
                }
              },
              "title": "Error Message",
              "type": "object"
            }
          }
        },
        "description": "Unprocessable Entity"
      },
      "500": {
        "content": {
          "text/plain": {
            "schema": {
              "description": "A plain message informing, that an internal server error occured. In this case please send a mail with the full URL that caused the issue to support@unusualwhales.com.",
              "example": "Something went wrong",
              "title": "Error Message on an internal server error.",
              "type": "string"
            }
          }
        },
        "description": "Internal Server Error"
      }
    },
    "summary": "Information",
    "tags": [
      "etfs"
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

## GET /api/etfs/{ticker}/weights

Sector & Country weights

Returns the sector & country weights for the given ETF ticker.


### Fully resolved operation
```json
{
  "key": "GET /api/etfs/{ticker}/weights",
  "method": "GET",
  "path": "/api/etfs/{ticker}/weights",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "Returns the sector & country weights for the given ETF ticker.\n",
    "operationId": "PublicApi.EtfController.weights",
    "parameters": [
      {
        "description": "",
        "in": "path",
        "name": "ticker",
        "required": true,
        "schema": {
          "description": "A single ticker",
          "example": "AAPL",
          "title": "SingleTicker",
          "type": "string"
        }
      }
    ],
    "responses": {
      "200": {
        "content": {
          "application/json": {
            "schema": {
              "description": "",
              "example": {
                "country": [
                  {
                    "country": "Ireland",
                    "weight": "0.0164"
                  },
                  {
                    "country": "Other",
                    "weight": "0.0059"
                  },
                  {
                    "country": "Switzerland",
                    "weight": "0.0043"
                  },
                  {
                    "country": "Netherlands",
                    "weight": "0.0015"
                  },
                  {
                    "country": "Canada",
                    "weight": "0.0014"
                  },
                  {
                    "country": "Bermuda",
                    "weight": "0.0011"
                  },
                  {
                    "country": "Israel",
                    "weight": "0.0001"
                  },
                  {
                    "country": "United States",
                    "weight": "0.9693"
                  }
                ],
                "sector": [
                  {
                    "sector": "Basic Materials",
                    "weight": "0.022"
                  },
                  {
                    "sector": "Communication Services",
                    "weight": "0.0861"
                  },
                  {
                    "sector": "Consumer Cyclical",
                    "weight": "0.1091"
                  },
                  {
                    "sector": "Consumer Defensive",
                    "weight": "0.0626"
                  },
                  {
                    "sector": "Energy",
                    "weight": "0.041"
                  },
                  {
                    "sector": "Financial Services",
                    "weight": "0.125"
                  },
                  {
                    "sector": "Healthcare",
                    "weight": "0.1272"
                  },
                  {
                    "sector": "Industrials",
                    "weight": "0.0816"
                  },
                  {
                    "sector": "Other",
                    "weight": "0.00009999999999990905"
                  },
                  {
                    "sector": "Real Estate",
                    "weight": "0.0243"
                  },
                  {
                    "sector": "Technology",
                    "weight": "0.2971"
                  },
                  {
                    "sector": "Utilities",
                    "weight": "0.0239"
                  }
                ]
              },
              "properties": {
                "country": {
                  "description": "A list of countries with their exposure by percentage.",
                  "example": "[\n  {\n    \"country\": \"Netherlands\",\n    \"weight\": \"0.0015\"\n  },\n  {\n    \"country\": \"Canada\",\n    \"weight\": \"0.0014\"\n  }\n]\n",
                  "items": {
                    "description": "A country and it's corresponding exposure in percentage.",
                    "example": "{\n  \"country\": \"Switzerland\",\n  \"weight\": \"0.0043\"\n}\n",
                    "properties": {
                      "country": {
                        "description": "The country.",
                        "example": "Ireland",
                        "type": "string"
                      },
                      "weight": {
                        "description": "The country exposure in percentage.",
                        "example": "0.0164",
                        "type": "string"
                      }
                    },
                    "type": "object"
                  },
                  "title": "Etf Countries",
                  "type": "array"
                },
                "sector": {
                  "description": "A list of sectors with their exposure by percentage.",
                  "example": "[\n  {\n    \"sector\": \"Basic Materials\",\n    \"weight\": \"0.022\"\n  },\n  {\n    \"sector\": \"Communication Services\",\n    \"weight\": \"0.0861\"\n  }\n]\n",
                  "items": {
                    "description": "A sector and it's corresponding exposure in percentage.",
                    "example": "{\n  \"sector\": \"Basic Materials\",\n  \"weight\": \"0.022\"\n}\n",
                    "properties": {
                      "sector": {
                        "description": "The sector.",
                        "example": "Healthcare",
                        "type": "string"
                      },
                      "weight": {
                        "description": "The sector exposure in percentage.",
                        "example": "0.1272",
                        "type": "string"
                      }
                    },
                    "type": "object"
                  },
                  "title": "Etf Sectors",
                  "type": "array"
                }
              },
              "title": "Country & Sector exposure",
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
      },
      "422": {
        "content": {
          "application/json": {
            "schema": {
              "description": "A json object containing information on the error cause.",
              "example": {
                "msg": "Invalid path input: MSFT12 (valid example: AAPL) - Invalid query input(s): date=2023-02-140 (valid example: date=2024-01-18)",
                "path": "/api/darkpool/MSFT12",
                "query": "date=2023-02-140",
                "url": "localhost:4000/api/darkpool/MSFT12?date=2023-02-140"
              },
              "properties": {
                "msg": {
                  "description": "An error message containing information about the faulty input.",
                  "type": "string"
                },
                "path": {
                  "description": "The URL path segment.",
                  "type": "string"
                },
                "query": {
                  "description": "The URL query segment.",
                  "type": "string"
                },
                "url": {
                  "description": "The full URL causing the error.",
                  "type": "string"
                }
              },
              "title": "Error Message",
              "type": "object"
            }
          }
        },
        "description": "Unprocessable Entity"
      },
      "500": {
        "content": {
          "text/plain": {
            "schema": {
              "description": "A plain message informing, that an internal server error occured. In this case please send a mail with the full URL that caused the issue to support@unusualwhales.com.",
              "example": "Something went wrong",
              "title": "Error Message on an internal server error.",
              "type": "string"
            }
          }
        },
        "description": "Internal Server Error"
      }
    },
    "summary": "Sector & Country weights",
    "tags": [
      "etfs"
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
