# lit-flow

Source: https://api.unusualwhales.com/docs/openapi.yaml; retrieved 2026-09-24T01:21:27.462441+00:00

Full descriptions, inherited security, effective parameters, responses and schemas. No live calls.

## GET /api/lit-flow/recent

Recent Lit Flow Trades

Returns the latest lit exchange trades.


### Fully resolved operation
```json
{
  "key": "GET /api/lit-flow/recent",
  "method": "GET",
  "path": "/api/lit-flow/recent",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "Returns the latest lit exchange trades.\n",
    "operationId": "PublicApi.LitFlowController.lit_flow_recent",
    "parameters": [
      {
        "description": "",
        "in": "query",
        "name": "limit",
        "required": false,
        "schema": {
          "default": 100,
          "description": "How many items to return. Default: 100. Max: 200. Min: 1.",
          "example": 10,
          "maximum": 200,
          "minimum": 1,
          "title": "Default 100 Max 200 Min 1",
          "type": "integer"
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
      },
      {
        "description": "",
        "in": "query",
        "name": "min_premium",
        "required": false,
        "schema": {
          "default": 0,
          "description": "The minimum premium requested trades should have.",
          "example": 50000,
          "minimum": 0,
          "title": "StockTradesMinPremium",
          "type": "integer"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "max_premium",
        "required": false,
        "schema": {
          "description": "The maximum premium requested trades should have.",
          "example": 150000,
          "title": "StockTradesMaxPremium",
          "type": "integer"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "min_size",
        "required": false,
        "schema": {
          "default": 0,
          "description": "The minimum size requested trades should have. Must be a positive integer.",
          "example": 50000,
          "minimum": 0,
          "title": "StockTradesMinSize",
          "type": "integer"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "max_size",
        "required": false,
        "schema": {
          "description": "The maximum size requested trades should have. Must be a positive integer.",
          "example": 150000,
          "title": "StockTradesMaxSize",
          "type": "integer"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "min_volume",
        "required": false,
        "schema": {
          "default": 0,
          "description": "The minimum consolidated volume requested trades should have. Must be a positive integer.",
          "example": 50000,
          "minimum": 0,
          "title": "StockTradesMinVol",
          "type": "integer"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "max_volume",
        "required": false,
        "schema": {
          "description": "The maximum consolidated volume requested trades should have. Must be a positive integer.",
          "example": 150000,
          "title": "StockTradesMaxVol",
          "type": "integer"
        }
      }
    ],
    "responses": {
      "200": {
        "content": {
          "application/json": {
            "schema": {
              "description": "A lit exchange trade.",
              "example": {
                "data": [
                  {
                    "canceled": false,
                    "executed_at": "2023-02-16 14:30:44+00:00",
                    "ext_hour_sold_codes": null,
                    "market_center": "Q",
                    "nbbo_ask": "185.50",
                    "nbbo_ask_quantity": 400,
                    "nbbo_bid": "185.45",
                    "nbbo_bid_quantity": 800,
                    "premium": "1854500.00",
                    "price": "185.45",
                    "sale_cond_codes": "regular_sale",
                    "size": 10000,
                    "ticker": "AAPL",
                    "tracking_id": 71984388012245,
                    "trade_code": null,
                    "trade_settlement": "regular_settlement",
                    "volume": 15946819
                  },
                  {
                    "canceled": false,
                    "executed_at": "2023-02-16 14:30:42+00:00",
                    "ext_hour_sold_codes": null,
                    "market_center": "N",
                    "nbbo_ask": "185.52",
                    "nbbo_ask_quantity": 300,
                    "nbbo_bid": "185.48",
                    "nbbo_bid_quantity": 600,
                    "premium": "927400.00",
                    "price": "185.48",
                    "sale_cond_codes": "regular_sale",
                    "size": 5000,
                    "ticker": "AAPL",
                    "tracking_id": 71984384768588,
                    "trade_code": null,
                    "trade_settlement": "regular_settlement",
                    "volume": 15936819
                  }
                ]
              },
              "properties": {
                "canceled": {
                  "description": "Whether the trade has been cancelled.",
                  "example": true,
                  "title": "Single Trade Is Trade Cancelled",
                  "type": "boolean"
                },
                "executed_at": {
                  "description": "The trade execution time as an ISO 8601 UTC timestamp.",
                  "example": "2023-02-16 00:59:44+00:00",
                  "format": "date-time",
                  "title": "Single Trade Execution Time",
                  "type": "string"
                },
                "ext_hour_sold_codes": {
                  "description": "The code describing why the trade happened outside of regular market hours. Null if none applies.",
                  "enum": [
                    "sold_out_of_sequence",
                    "extended_hours_trade_late_or_out_of_sequence",
                    "extended_hours_trade"
                  ],
                  "example": "sold_out_of_sequence",
                  "title": "Single Trade External Hour Sold Code",
                  "type": "string"
                },
                "market_center": {
                  "description": "The market center code.",
                  "example": "L",
                  "title": "Single Trade Market Center",
                  "type": "string"
                },
                "nbbo_ask": {
                  "description": "",
                  "title": "ToBeDone"
                },
                "nbbo_ask_quantity": {
                  "description": "",
                  "title": "ToBeDone"
                },
                "nbbo_bid": {
                  "description": "",
                  "title": "ToBeDone"
                },
                "nbbo_bid_quantity": {
                  "description": "",
                  "title": "ToBeDone"
                },
                "premium": {
                  "description": "The total option premium.",
                  "example": "27723806.00",
                  "title": "Option Contract Premium",
                  "type": "string"
                },
                "price": {
                  "description": "The price of the trade.",
                  "example": "18.9904",
                  "title": "Single Trade Price",
                  "type": "string"
                },
                "sale_cond_codes": {
                  "description": "The sale condition code. Null if none applies.",
                  "enum": [
                    "contingent_trade",
                    "odd_lot_execution",
                    "prior_reference_price",
                    "average_price_trade"
                  ],
                  "example": "contingent_trade",
                  "title": "Single Trade Sale Cond Code",
                  "type": "string"
                },
                "size": {
                  "description": "The size of the transaction.",
                  "example": 6400,
                  "title": "Single Trade Size",
                  "type": "integer"
                },
                "ticker": {
                  "description": "The stock ticker.",
                  "example": "AAPL",
                  "title": "Stock Ticker",
                  "type": "string"
                },
                "tracking_id": {
                  "description": "The tracking ID of the trade.",
                  "example": 71984388012245,
                  "title": "Single Trade Tracking ID",
                  "type": "integer"
                },
                "trade_code": {
                  "description": "The trade code. Null if none applies.",
                  "enum": [
                    "derivative_priced",
                    "qualified_contingent_trade",
                    "intermarket_sweep"
                  ],
                  "example": "derivative_priced",
                  "title": "Single Trade Trade Code",
                  "type": "string"
                },
                "trade_settlement": {
                  "description": "The kind of trade settlement.",
                  "enum": [
                    "cash",
                    "next_day",
                    "seller",
                    "regular"
                  ],
                  "example": "cash_settlement",
                  "title": "Single Trade Settlement",
                  "type": "string"
                },
                "volume": {
                  "description": "The volume of the ticker for the trading day.",
                  "example": 23132119,
                  "title": "Stock Day Stock Volume",
                  "type": "integer"
                }
              },
              "title": "Lit Trade",
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
    "summary": "Recent Lit Flow Trades",
    "tags": [
      "lit-flow"
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

## GET /api/lit-flow/{ticker}

Ticker Lit Flow Trades

Returns the lit exchange trades for the given ticker on a given day.
Date must be the current or a past date. If no date is given, returns data for the current/last market day.


### Fully resolved operation
```json
{
  "key": "GET /api/lit-flow/{ticker}",
  "method": "GET",
  "path": "/api/lit-flow/{ticker}",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "Returns the lit exchange trades for the given ticker on a given day.\nDate must be the current or a past date. If no date is given, returns data for the current/last market day.\n",
    "operationId": "PublicApi.LitFlowController.lit_flow_ticker",
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
        "name": "date",
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
        "name": "newer_than",
        "required": false,
        "schema": {
          "description": "The unix time in milliseconds or seconds at which no older results will be returned. Can be used with `older_than` to paginate by time. Also accepts an ISO date or RFC 3339 datetime (example: 2024-01-25).",
          "example": 1715083417,
          "title": "NewerThan",
          "type": "string"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "older_than",
        "required": false,
        "schema": {
          "description": "The unix time in milliseconds or seconds at which no newer results will be returned. Can be used with `newer_than` to paginate by time. Also accepts an ISO date or RFC 3339 datetime (example: 2024-01-25).",
          "example": 1715083417,
          "title": "OlderThan",
          "type": "string"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "min_premium",
        "required": false,
        "schema": {
          "default": 0,
          "description": "The minimum premium requested trades should have.",
          "example": 50000,
          "minimum": 0,
          "title": "StockTradesMinPremium",
          "type": "integer"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "max_premium",
        "required": false,
        "schema": {
          "description": "The maximum premium requested trades should have.",
          "example": 150000,
          "title": "StockTradesMaxPremium",
          "type": "integer"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "min_size",
        "required": false,
        "schema": {
          "default": 0,
          "description": "The minimum size requested trades should have. Must be a positive integer.",
          "example": 50000,
          "minimum": 0,
          "title": "StockTradesMinSize",
          "type": "integer"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "max_size",
        "required": false,
        "schema": {
          "description": "The maximum size requested trades should have. Must be a positive integer.",
          "example": 150000,
          "title": "StockTradesMaxSize",
          "type": "integer"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "min_volume",
        "required": false,
        "schema": {
          "default": 0,
          "description": "The minimum consolidated volume requested trades should have. Must be a positive integer.",
          "example": 50000,
          "minimum": 0,
          "title": "StockTradesMinVol",
          "type": "integer"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "max_volume",
        "required": false,
        "schema": {
          "description": "The maximum consolidated volume requested trades should have. Must be a positive integer.",
          "example": 150000,
          "title": "StockTradesMaxVol",
          "type": "integer"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "limit",
        "required": false,
        "schema": {
          "default": 500,
          "description": "How many items to return. Default: 500. Max: 500. Min: 1.",
          "example": 10,
          "maximum": 500,
          "minimum": 1,
          "title": "Default 500 Max 500 Min 1",
          "type": "integer"
        }
      }
    ],
    "responses": {
      "200": {
        "content": {
          "application/json": {
            "schema": {
              "description": "A lit exchange trade.",
              "example": {
                "data": [
                  {
                    "canceled": false,
                    "executed_at": "2023-02-16 14:30:44+00:00",
                    "ext_hour_sold_codes": null,
                    "market_center": "Q",
                    "nbbo_ask": "185.50",
                    "nbbo_ask_quantity": 400,
                    "nbbo_bid": "185.45",
                    "nbbo_bid_quantity": 800,
                    "premium": "1854500.00",
                    "price": "185.45",
                    "sale_cond_codes": "regular_sale",
                    "size": 10000,
                    "ticker": "AAPL",
                    "tracking_id": 71984388012245,
                    "trade_code": null,
                    "trade_settlement": "regular_settlement",
                    "volume": 15946819
                  },
                  {
                    "canceled": false,
                    "executed_at": "2023-02-16 14:30:42+00:00",
                    "ext_hour_sold_codes": null,
                    "market_center": "N",
                    "nbbo_ask": "185.52",
                    "nbbo_ask_quantity": 300,
                    "nbbo_bid": "185.48",
                    "nbbo_bid_quantity": 600,
                    "premium": "927400.00",
                    "price": "185.48",
                    "sale_cond_codes": "regular_sale",
                    "size": 5000,
                    "ticker": "AAPL",
                    "tracking_id": 71984384768588,
                    "trade_code": null,
                    "trade_settlement": "regular_settlement",
                    "volume": 15936819
                  }
                ]
              },
              "properties": {
                "canceled": {
                  "description": "Whether the trade has been cancelled.",
                  "example": true,
                  "title": "Single Trade Is Trade Cancelled",
                  "type": "boolean"
                },
                "executed_at": {
                  "description": "The trade execution time as an ISO 8601 UTC timestamp.",
                  "example": "2023-02-16 00:59:44+00:00",
                  "format": "date-time",
                  "title": "Single Trade Execution Time",
                  "type": "string"
                },
                "ext_hour_sold_codes": {
                  "description": "The code describing why the trade happened outside of regular market hours. Null if none applies.",
                  "enum": [
                    "sold_out_of_sequence",
                    "extended_hours_trade_late_or_out_of_sequence",
                    "extended_hours_trade"
                  ],
                  "example": "sold_out_of_sequence",
                  "title": "Single Trade External Hour Sold Code",
                  "type": "string"
                },
                "market_center": {
                  "description": "The market center code.",
                  "example": "L",
                  "title": "Single Trade Market Center",
                  "type": "string"
                },
                "nbbo_ask": {
                  "description": "",
                  "title": "ToBeDone"
                },
                "nbbo_ask_quantity": {
                  "description": "",
                  "title": "ToBeDone"
                },
                "nbbo_bid": {
                  "description": "",
                  "title": "ToBeDone"
                },
                "nbbo_bid_quantity": {
                  "description": "",
                  "title": "ToBeDone"
                },
                "premium": {
                  "description": "The total option premium.",
                  "example": "27723806.00",
                  "title": "Option Contract Premium",
                  "type": "string"
                },
                "price": {
                  "description": "The price of the trade.",
                  "example": "18.9904",
                  "title": "Single Trade Price",
                  "type": "string"
                },
                "sale_cond_codes": {
                  "description": "The sale condition code. Null if none applies.",
                  "enum": [
                    "contingent_trade",
                    "odd_lot_execution",
                    "prior_reference_price",
                    "average_price_trade"
                  ],
                  "example": "contingent_trade",
                  "title": "Single Trade Sale Cond Code",
                  "type": "string"
                },
                "size": {
                  "description": "The size of the transaction.",
                  "example": 6400,
                  "title": "Single Trade Size",
                  "type": "integer"
                },
                "ticker": {
                  "description": "The stock ticker.",
                  "example": "AAPL",
                  "title": "Stock Ticker",
                  "type": "string"
                },
                "tracking_id": {
                  "description": "The tracking ID of the trade.",
                  "example": 71984388012245,
                  "title": "Single Trade Tracking ID",
                  "type": "integer"
                },
                "trade_code": {
                  "description": "The trade code. Null if none applies.",
                  "enum": [
                    "derivative_priced",
                    "qualified_contingent_trade",
                    "intermarket_sweep"
                  ],
                  "example": "derivative_priced",
                  "title": "Single Trade Trade Code",
                  "type": "string"
                },
                "trade_settlement": {
                  "description": "The kind of trade settlement.",
                  "enum": [
                    "cash",
                    "next_day",
                    "seller",
                    "regular"
                  ],
                  "example": "cash_settlement",
                  "title": "Single Trade Settlement",
                  "type": "string"
                },
                "volume": {
                  "description": "The volume of the ticker for the trading day.",
                  "example": 23132119,
                  "title": "Stock Day Stock Volume",
                  "type": "integer"
                }
              },
              "title": "Lit Trade",
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
    "summary": "Ticker Lit Flow Trades",
    "tags": [
      "lit-flow"
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
