# seasonality

Source: https://api.unusualwhales.com/docs/openapi.yaml; retrieved 2026-09-24T01:21:27.462441+00:00

Full descriptions, inherited security, effective parameters, responses and schemas. No live calls.

## GET /api/seasonality/market

Market Seasonality

Returns the average return by month for the tickers SPY, QQQ, IWM, XLE, XLC, XLK, XLV, XLP, XLY, XLRE, XLF, XLI, XLB .


### Fully resolved operation
```json
{
  "key": "GET /api/seasonality/market",
  "method": "GET",
  "path": "/api/seasonality/market",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "Returns the average return by month for the tickers SPY, QQQ, IWM, XLE, XLC, XLK, XLV, XLP, XLY, XLRE, XLF, XLI, XLB .\n",
    "operationId": "PublicApi.SeasonalityController.market_seasonality",
    "parameters": [],
    "responses": {
      "200": {
        "content": {
          "application/json": {
            "schema": {
              "description": "The price change for the ticker over the given count of years.\n",
              "example": {
                "data": [
                  {
                    "avg_change": "-0.0068",
                    "max_change": "0.0642",
                    "median_change": "-0.0041",
                    "min_change": "-0.0913",
                    "month": 6,
                    "positive_closes": 7,
                    "positive_months_perc": "0.4375",
                    "ticker": "SPY",
                    "years": 16
                  },
                  {
                    "avg_change": "0.0038",
                    "max_change": "0.0666",
                    "median_change": "0.0115",
                    "min_change": "-0.0838",
                    "month": 5,
                    "positive_closes": 13,
                    "positive_months_perc": "0.8125",
                    "ticker": "SPY",
                    "years": 16
                  },
                  {
                    "avg_change": "0.0092",
                    "max_change": "0.0791",
                    "median_change": "0.0367",
                    "min_change": "-0.1614",
                    "month": 3,
                    "positive_closes": 5,
                    "positive_months_perc": "0.7142",
                    "ticker": "XLRE",
                    "years": 7
                  },
                  {
                    "avg_change": "0.0044",
                    "max_change": "0.0697",
                    "median_change": "-0.0032",
                    "min_change": "-0.0651",
                    "month": 2,
                    "positive_closes": 8,
                    "positive_months_perc": "0.4705",
                    "ticker": "QQQ",
                    "years": 17
                  },
                  {
                    "avg_change": "0.0201",
                    "max_change": "0.1459",
                    "median_change": "-0.0034",
                    "min_change": "-0.0401",
                    "month": 4,
                    "positive_closes": 3,
                    "positive_months_perc": "0.4285",
                    "ticker": "XLRE",
                    "years": 7
                  }
                ]
              },
              "properties": {
                "avg_change": {
                  "description": "The average relative price change per day for the month.",
                  "example": 0.09494354167379757,
                  "title": "Seasonality Average Change",
                  "type": "number"
                },
                "max_change": {
                  "description": "The maximum relative price change per day for the month.",
                  "example": 0.14970489711277724,
                  "title": "Seasonality Max Change",
                  "type": "number"
                },
                "median_change": {
                  "description": "The median relative price change per day for the month.",
                  "example": 0.09494354167379757,
                  "title": "Seasonality Median Change",
                  "type": "number"
                },
                "min_change": {
                  "description": "The minimum relative price change per day for the month.",
                  "example": 0.0401821862348179,
                  "title": "Seasonality Min Change",
                  "type": "number"
                },
                "month": {
                  "description": "The number indicating the month the data applies for. e.g. 1 -> January, 2 -> February, ...",
                  "example": 5,
                  "title": "Seasonality Month Number",
                  "type": "integer"
                },
                "positive_closes": {
                  "description": "The number of years, the month had a positive close.",
                  "example": 2,
                  "title": "Seasonality Positive Closes Count",
                  "type": "integer"
                },
                "positive_months_perc": {
                  "description": "The relative amount of times, the month had a positive close. Multiply with 100 to get the amount in percent.",
                  "example": 0.6667,
                  "title": "Seasonality Positive Months Percent",
                  "type": "number"
                },
                "ticker": {
                  "description": "The stock ticker.",
                  "example": "AAPL",
                  "title": "Stock Ticker",
                  "type": "string"
                },
                "years": {
                  "description": "The number of years used to calculate the data.",
                  "example": 3,
                  "title": "Seasonality Year Count",
                  "type": "number"
                }
              },
              "title": "Seasonality Market",
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
    "summary": "Market Seasonality",
    "tags": [
      "seasonality"
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

## GET /api/seasonality/{month}/performers

Month Performers

Returns the tickers with the highest performance in terms of price change in the month over the years.
Per default the result is ordered by 'positive_months_perc' descending, then 'median_change' descending, then 'marketcap' descending.


### Fully resolved operation
```json
{
  "key": "GET /api/seasonality/{month}/performers",
  "method": "GET",
  "path": "/api/seasonality/{month}/performers",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "Returns the tickers with the highest performance in terms of price change in the month over the years.\nPer default the result is ordered by 'positive_months_perc' descending, then 'median_change' descending, then 'marketcap' descending.\n",
    "operationId": "PublicApi.SeasonalityController.month_performers",
    "parameters": [
      {
        "description": "",
        "in": "path",
        "name": "month",
        "required": true,
        "schema": {
          "description": "A month number indicating the month, e.g. 1 -> January, 2 -> February, ...",
          "enum": [
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "10",
            "11",
            "12"
          ],
          "example": "3",
          "title": "SingleMonthNumber",
          "type": "string"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "min_years",
        "required": false,
        "schema": {
          "default": 10,
          "description": "The minimum amount of years data for the month need to be available for the ticker. Default: 10. Min: 1.",
          "example": 3,
          "minimum": 1,
          "title": "Min Years",
          "type": "integer"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "ticker_for_sector",
        "required": false,
        "schema": {
          "description": "A single ticker. The result will only contain tickers in the same sector as the given ticker, e.g. 'MSFT' will only yield result tickers in sector 'Technology'.",
          "example": "AAPL",
          "title": "SingleTickerForSector",
          "type": "string"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "s_p_500_nasdaq_only",
        "required": false,
        "schema": {
          "default": false,
          "description": "Only return tickers, that are in the S&P 500 index or the Nasdaq 100 index.",
          "example": true,
          "title": "S&P 500/Nasdaq Only",
          "type": "boolean"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "min_oi",
        "required": false,
        "schema": {
          "description": "The minimum open interest. Min: 0.",
          "example": 10000,
          "minimum": 0,
          "title": "Min Open Interest",
          "type": "integer"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "limit",
        "required": false,
        "schema": {
          "default": 50,
          "description": "How many items to return. Default: 50. Min: 1.",
          "example": 10,
          "minimum": 1,
          "title": "Seasonality Performers Limit",
          "type": "integer"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "order",
        "required": false,
        "schema": {
          "description": "Optional columns to order the result by",
          "enum": [
            "month",
            "positive_closes",
            "years",
            "positive_months_perc",
            "median_change",
            "avg_change",
            "max_change",
            "min_change"
          ],
          "example": "ticker",
          "title": "Seasonality Performance Order By",
          "type": "string"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "order_direction",
        "required": false,
        "schema": {
          "default": "desc",
          "description": "Whether to sort descending or ascending. Descending by default.",
          "enum": [
            "desc",
            "asc"
          ],
          "example": "asc",
          "title": "OrderDirection",
          "type": "string"
        }
      }
    ],
    "responses": {
      "200": {
        "content": {
          "application/json": {
            "schema": {
              "description": "The price change for the ticker over the given count of years.\n",
              "example": {
                "data": [
                  {
                    "avg_change": "0.0592",
                    "marketcap": "19427901578",
                    "max_change": "0.1104",
                    "median_change": "0.0639",
                    "min_change": "0.0091",
                    "month": 5,
                    "positive_closes": 11,
                    "positive_months_perc": "1.1",
                    "sector": "Healthcare",
                    "ticker": "ICLR",
                    "years": 10
                  },
                  {
                    "avg_change": "0.0577",
                    "marketcap": "1927713687",
                    "max_change": "0.2301",
                    "median_change": "0.0417",
                    "min_change": "-0.2485",
                    "month": 5,
                    "positive_closes": 10,
                    "positive_months_perc": "1",
                    "sector": "Technology",
                    "ticker": "AMBA",
                    "years": 10
                  },
                  {
                    "avg_change": "0.0664",
                    "marketcap": "60982620879",
                    "max_change": "0.1791",
                    "median_change": "0.07291",
                    "min_change": "-0.0878",
                    "month": 5,
                    "positive_closes": 15,
                    "positive_months_perc": "0.9375",
                    "sector": "Healthcare",
                    "ticker": "MCK",
                    "years": 16
                  },
                  {
                    "avg_change": "0.0674",
                    "marketcap": "24233152429",
                    "max_change": "0.2167",
                    "median_change": "0.0723",
                    "min_change": "-0.1812",
                    "month": 5,
                    "positive_closes": 15,
                    "positive_months_perc": "0.9375",
                    "sector": "Communication Services",
                    "ticker": "TTWO",
                    "years": 16
                  }
                ]
              },
              "properties": {
                "avg_change": {
                  "description": "The average relative price change per day for the month.",
                  "example": 0.09494354167379757,
                  "title": "Seasonality Average Change",
                  "type": "number"
                },
                "marketcap": {
                  "description": "The marketcap of the underlying ticker. If the issue type of the ticker is ETF then the marketcap represents the AUM.",
                  "example": "2965813810400",
                  "title": "Stock Marketcap AUM",
                  "type": "string"
                },
                "max_change": {
                  "description": "The maximum relative price change per day for the month.",
                  "example": 0.14970489711277724,
                  "title": "Seasonality Max Change",
                  "type": "number"
                },
                "median_change": {
                  "description": "The median relative price change per day for the month.",
                  "example": 0.09494354167379757,
                  "title": "Seasonality Median Change",
                  "type": "number"
                },
                "min_change": {
                  "description": "The minimum relative price change per day for the month.",
                  "example": 0.0401821862348179,
                  "title": "Seasonality Min Change",
                  "type": "number"
                },
                "month": {
                  "description": "The number indicating the month the data applies for. e.g. 1 -> January, 2 -> February, ...",
                  "example": 5,
                  "title": "Seasonality Month Number",
                  "type": "integer"
                },
                "positive_closes": {
                  "description": "The number of years, the month had a positive close.",
                  "example": 2,
                  "title": "Seasonality Positive Closes Count",
                  "type": "integer"
                },
                "positive_months_perc": {
                  "description": "The relative amount of times, the month had a positive close. Multiply with 100 to get the amount in percent.",
                  "example": 0.6667,
                  "title": "Seasonality Positive Months Percent",
                  "type": "number"
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
                "years": {
                  "description": "The number of years used to calculate the data.",
                  "example": 3,
                  "title": "Seasonality Year Count",
                  "type": "number"
                }
              },
              "title": "Seasonality Performers",
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
    "summary": "Month Performers",
    "tags": [
      "seasonality"
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

## GET /api/seasonality/{ticker}/monthly

Average return per month

Returns the average return by month for the given ticker.


### Fully resolved operation
```json
{
  "key": "GET /api/seasonality/{ticker}/monthly",
  "method": "GET",
  "path": "/api/seasonality/{ticker}/monthly",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "Returns the average return by month for the given ticker.\n",
    "operationId": "PublicApi.SeasonalityController.monthly",
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
              "description": "The price change for the ticker in the month over the given count of years.\n",
              "example": {
                "data": [
                  {
                    "avg_change": 0.0034,
                    "max_change": 0.0635,
                    "median_change": 0.0195,
                    "min_change": -0.0727,
                    "month": 1,
                    "positive_closes": 2,
                    "positive_months_perc": 0.6667,
                    "years": 3
                  },
                  {
                    "avg_change": 0.0006,
                    "max_change": 0.0334,
                    "median_change": 0.0057,
                    "min_change": -0.0374,
                    "month": 2,
                    "positive_closes": 2,
                    "positive_months_perc": 0.6667,
                    "years": 3
                  },
                  {
                    "avg_change": 0.0949,
                    "max_change": 0.1497,
                    "median_change": 0.0949,
                    "min_change": 0.0402,
                    "month": 3,
                    "positive_closes": 2,
                    "positive_months_perc": 1,
                    "years": 2
                  },
                  {
                    "avg_change": -0.0153,
                    "max_change": 0.0724,
                    "median_change": -0.0153,
                    "min_change": -0.1029,
                    "month": 4,
                    "positive_closes": 1,
                    "positive_months_perc": 0.5,
                    "years": 2
                  }
                ]
              },
              "properties": {
                "avg_change": {
                  "description": "The average relative price change per day for the month.",
                  "example": 0.09494354167379757,
                  "title": "Seasonality Average Change",
                  "type": "number"
                },
                "max_change": {
                  "description": "The maximum relative price change per day for the month.",
                  "example": 0.14970489711277724,
                  "title": "Seasonality Max Change",
                  "type": "number"
                },
                "median_change": {
                  "description": "The median relative price change per day for the month.",
                  "example": 0.09494354167379757,
                  "title": "Seasonality Median Change",
                  "type": "number"
                },
                "min_change": {
                  "description": "The minimum relative price change per day for the month.",
                  "example": 0.0401821862348179,
                  "title": "Seasonality Min Change",
                  "type": "number"
                },
                "month": {
                  "description": "The number indicating the month the data applies for. e.g. 1 -> January, 2 -> February, ...",
                  "example": 5,
                  "title": "Seasonality Month Number",
                  "type": "integer"
                },
                "positive_closes": {
                  "description": "The number of years, the month had a positive close.",
                  "example": 2,
                  "title": "Seasonality Positive Closes Count",
                  "type": "integer"
                },
                "positive_months_perc": {
                  "description": "The relative amount of times, the month had a positive close. Multiply with 100 to get the amount in percent.",
                  "example": 0.6667,
                  "title": "Seasonality Positive Months Percent",
                  "type": "number"
                },
                "years": {
                  "description": "The number of years used to calculate the data.",
                  "example": 3,
                  "title": "Seasonality Year Count",
                  "type": "number"
                }
              },
              "title": "Seasonality Monthly",
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
    "summary": "Average return per month",
    "tags": [
      "seasonality"
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

## GET /api/seasonality/{ticker}/year-month

Price change per month per year

Returns the relative price change for all past months over multiple years.


### Fully resolved operation
```json
{
  "key": "GET /api/seasonality/{ticker}/year-month",
  "method": "GET",
  "path": "/api/seasonality/{ticker}/year-month",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "Returns the relative price change for all past months over multiple years.\n",
    "operationId": "PublicApi.SeasonalityController.year_month",
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
              "description": "The price change for the ticker in the month in the year.\n",
              "example": {
                "data": [
                  {
                    "change": "-0.0469",
                    "close": 315.75,
                    "month": 9,
                    "open": 331.31,
                    "year": 2023
                  },
                  {
                    "change": "0.0690",
                    "close": 338.11,
                    "month": 10,
                    "open": 316.28,
                    "year": 2023
                  },
                  {
                    "change": "0.1151",
                    "close": 378.91,
                    "month": 11,
                    "open": 339.79,
                    "year": 2023
                  },
                  {
                    "change": "-0.0019",
                    "close": 376.04,
                    "month": 12,
                    "open": 376.76,
                    "year": 2023
                  },
                  {
                    "change": "0.0634",
                    "close": 397.58,
                    "month": 1,
                    "open": 373.86,
                    "year": 2024
                  }
                ]
              },
              "properties": {
                "change": {
                  "description": "The relative price change for the month.",
                  "example": 0.09494354167379757,
                  "title": "Seasonality Change",
                  "type": "number"
                },
                "close": {
                  "description": "The closing stock price of the ticker for the month.",
                  "example": "182.91",
                  "title": "Seasonality Close Price",
                  "type": "string"
                },
                "month": {
                  "description": "The number indicating the month the data applies for. e.g. 1 -> January, 2 -> February, ...",
                  "example": 5,
                  "title": "Seasonality Month Number",
                  "type": "integer"
                },
                "open": {
                  "description": "The opening stock price of the ticker for the month.",
                  "example": "182.91",
                  "title": "Seasonality Open Price",
                  "type": "string"
                },
                "year": {
                  "description": "The Year.",
                  "example": 5,
                  "title": "Seasonality Year",
                  "type": "integer"
                }
              },
              "title": "Seasonality Year Month",
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
    "summary": "Price change per month per year",
    "tags": [
      "seasonality"
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
