# insiders

Source: https://api.unusualwhales.com/docs/openapi.yaml; retrieved 2026-09-24T01:21:27.462441+00:00

Full descriptions, inherited security, effective parameters, responses and schemas. No live calls.

## GET /api/insider/transactions

Transactions

Returns the latest insider transactions.

By default all transacations that have been filled by the same person on the same day with the same trade code are aggregated into a single row.
Each of those aggregated rows will contain a field `ids` which contains the ids of the single transactions that were aggregated as well as the amount
of transactions that were aggregated.

If you want to disable this behaviour you can set the `group` parameter to false to receive the single transacations as they have been filled.


### Fully resolved operation
```json
{
  "key": "GET /api/insider/transactions",
  "method": "GET",
  "path": "/api/insider/transactions",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "Returns the latest insider transactions.\n\nBy default all transacations that have been filled by the same person on the same day with the same trade code are aggregated into a single row.\nEach of those aggregated rows will contain a field `ids` which contains the ids of the single transactions that were aggregated as well as the amount\nof transactions that were aggregated.\n\nIf you want to disable this behaviour you can set the `group` parameter to false to receive the single transacations as they have been filled.\n",
    "operationId": "PublicApi.InsiderController.transactions",
    "parameters": [
      {
        "description": "",
        "in": "query",
        "name": "ticker_symbol",
        "required": false,
        "schema": {
          "description": "A comma separated list of tickers. To exclude certain tickers prefix the first ticker with a `-`.",
          "example": "AAPL,INTC",
          "title": "Ticker",
          "type": "string"
        }
      },
      {
        "description": "Minimum transaction value in dollars",
        "example": 100000,
        "in": "query",
        "name": "min_value",
        "required": false,
        "schema": {
          "type": "string"
        }
      },
      {
        "description": "Maximum transaction value in dollars",
        "example": 1000000,
        "in": "query",
        "name": "max_value",
        "required": false,
        "schema": {
          "type": "string"
        }
      },
      {
        "description": "Minimum stock price at the time of transaction",
        "example": 10.5,
        "in": "query",
        "name": "min_price",
        "required": false,
        "schema": {
          "type": "string"
        }
      },
      {
        "description": "Maximum stock price at the time of transaction",
        "example": 50.75,
        "in": "query",
        "name": "max_price",
        "required": false,
        "schema": {
          "type": "string"
        }
      },
      {
        "description": "Name of the insider who made the transaction",
        "example": "John Doe",
        "in": "query",
        "name": "owner_name",
        "required": false,
        "schema": {
          "type": "string"
        }
      },
      {
        "description": "Filter by company sector(s)",
        "in": "query",
        "name": "sectors[]",
        "required": false,
        "schema": {
          "description": "An array of 1 or more sectors.",
          "example": [
            "Consumer Cyclical",
            "Technology",
            "Utilities"
          ],
          "items": {
            "description": "A singular sector.",
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
            "example": "Real Estate",
            "title": "Single sector",
            "type": "string"
          },
          "title": "Sectors",
          "type": "array"
        }
      },
      {
        "description": "Filter by company industry or industries",
        "in": "query",
        "name": "industries[]",
        "required": false,
        "schema": {
          "description": "An array of one or more industries.",
          "example": [
            "Semiconductors",
            "Software - Infrastructure"
          ],
          "items": {
            "type": "string"
          },
          "title": "Industries",
          "type": "array"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "min_marketcap",
        "required": false,
        "schema": {
          "description": "The minimum marketcap. Min: 0.",
          "example": 1000000,
          "minimum": 0,
          "title": "Min Marketcap",
          "type": "number"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "max_marketcap",
        "required": false,
        "schema": {
          "description": "The maximum marketcap. Min: 0.",
          "example": 250000000,
          "minimum": 0,
          "title": "Max Marketcap",
          "type": "number"
        }
      },
      {
        "description": "Size category of company market cap",
        "in": "query",
        "name": "market_cap_size",
        "required": false,
        "schema": {
          "description": "A market capitalization size category.",
          "enum": [
            "micro",
            "small",
            "mid",
            "large",
            "big"
          ],
          "example": "large",
          "title": "Single market cap size",
          "type": "string"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "min_earnings_dte",
        "required": false,
        "schema": {
          "description": "The minimum days until the next earnings report.",
          "example": 5,
          "title": "Min Earnings DTE",
          "type": "integer"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "max_earnings_dte",
        "required": false,
        "schema": {
          "description": "The maximum days until the next earnings report.",
          "example": 30,
          "title": "Max Earnings DTE",
          "type": "integer"
        }
      },
      {
        "description": "Minimum number of shares in transaction",
        "example": 1000,
        "in": "query",
        "name": "min_amount",
        "required": false,
        "schema": {
          "type": "string"
        }
      },
      {
        "description": "Maximum number of shares in transaction",
        "example": 10000,
        "in": "query",
        "name": "max_amount",
        "required": false,
        "schema": {
          "type": "string"
        }
      },
      {
        "description": "Filter transactions by company directors",
        "example": true,
        "in": "query",
        "name": "is_director",
        "required": false,
        "schema": {
          "type": "boolean"
        }
      },
      {
        "description": "Filter transactions by company officers",
        "example": true,
        "in": "query",
        "name": "is_officer",
        "required": false,
        "schema": {
          "type": "boolean"
        }
      },
      {
        "description": "Only include S&P 500 companies",
        "example": true,
        "in": "query",
        "name": "is_s_p_500",
        "required": false,
        "schema": {
          "type": "boolean"
        }
      },
      {
        "description": "Filter transactions by 10% owners",
        "example": false,
        "in": "query",
        "name": "is_ten_percent_owner",
        "required": false,
        "schema": {
          "type": "boolean"
        }
      },
      {
        "description": "Only include common stock transactions",
        "example": true,
        "in": "query",
        "name": "common_stock_only",
        "required": false,
        "schema": {
          "type": "boolean"
        }
      },
      {
        "description": "Filter by transaction codes (P=Purchase, S=Sale, etc.)",
        "example": [
          "P",
          "S"
        ],
        "in": "query",
        "name": "transaction_codes[]",
        "required": false,
        "schema": {
          "type": "string"
        }
      },
      {
        "description": "Filter by SEC form: 3, 3/A, 4, 4/A, 5, 5/A, 144, 144/A. Form 144 is a notice of intended sale, so pass 4 (and 4/A for amendments) to get executed trades only. Default: all forms.",
        "example": [
          "4",
          "4/A"
        ],
        "in": "query",
        "name": "form_types[]",
        "required": false,
        "schema": {
          "type": "string"
        }
      },
      {
        "description": "Exact match on the reporting owner's SEC CIK. The stable identifier for one insider across companies and years; owner_name spelling varies between filings.",
        "example": "0001548760",
        "in": "query",
        "name": "reporter_cik",
        "required": false,
        "schema": {
          "type": "string"
        }
      },
      {
        "description": "Filter by security acquisition/disposition codes: NA, ND, DA, DD, D",
        "example": [
          "NA",
          "ND"
        ],
        "in": "query",
        "name": "security_ad_codes[]",
        "required": false,
        "schema": {
          "type": "string"
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
      },
      {
        "description": "",
        "in": "query",
        "name": "page",
        "required": false,
        "schema": {
          "description": "Page number (use with limit). Starts on page 0.",
          "example": 1,
          "title": "Page",
          "type": "integer"
        }
      },
      {
        "description": "Group insider transactions with same person and trade code on the same day into a single row",
        "example": true,
        "in": "query",
        "name": "group",
        "required": false,
        "schema": {
          "type": "boolean"
        }
      },
      {
        "description": "Filter for transaction dates occurring on or after this date (ISO format: YYYY-MM-DD)",
        "example": "2026-01-01",
        "in": "query",
        "name": "start_date",
        "required": false,
        "schema": {
          "format": "date",
          "type": "string"
        }
      },
      {
        "description": "Filter for transaction dates occurring on or before this date (ISO format: YYYY-MM-DD)",
        "example": "2026-01-23",
        "in": "query",
        "name": "end_date",
        "required": false,
        "schema": {
          "format": "date",
          "type": "string"
        }
      }
    ],
    "responses": {
      "200": {
        "content": {
          "application/json": {
            "schema": {
              "description": "An aggregated insider trade",
              "example": {
                "data": [
                  {
                    "amount": -35921,
                    "date_excercisable": null,
                    "director_indirect": null,
                    "expiration_date": null,
                    "filing_date": "2024-12-12",
                    "formtype": "144",
                    "id": "2662b73d-0ad6-4568-adb0-739b96c18090",
                    "ids": [
                      "26f2911d-8e40-4fd4-9b74-c450e203a0ad"
                    ],
                    "is_10b5_1": true,
                    "is_director": true,
                    "is_officer": true,
                    "is_s_p_500": true,
                    "is_ten_percent_owner": true,
                    "marketcap": "1375122749418",
                    "natureofownership": null,
                    "next_earnings_date": "2025-02-06",
                    "officer_title": "COB and CEO",
                    "owner_name": "ZUCKERBERG MARK",
                    "price": "632",
                    "price_excercisable": null,
                    "sector": "Communication Services",
                    "security_ad_code": null,
                    "security_title": null,
                    "shares_owned_after": null,
                    "shares_owned_before": null,
                    "stock_price": null,
                    "ticker": "META",
                    "transaction_code": "S",
                    "transaction_date": "2024-12-12",
                    "transactions": 1
                  }
                ]
              },
              "properties": {
                "accession_no": {
                  "description": "SEC EDGAR accession number of the filing this row came from.",
                  "example": "0001127602-24-012345",
                  "title": "Accession Number",
                  "type": "string"
                },
                "amended_original_accession_no": {
                  "description": "For /A amendments, the accession number of the filing being amended; null otherwise.",
                  "example": "0001127602-24-011111",
                  "nullable": true,
                  "title": "Amended Original Accession Number",
                  "type": "string"
                },
                "amount": {
                  "description": "The amount of the insider trade.",
                  "example": 1000,
                  "title": "Insider Amount",
                  "type": "integer"
                },
                "date_excercisable": {
                  "description": "The date excercisable of the insider trade.",
                  "example": "2023-12-06",
                  "title": "Insider Date Excercisable",
                  "type": "string"
                },
                "director_indirect": {
                  "description": "The director indirect of the insider trade.",
                  "example": "John Doe",
                  "title": "Insider Director Indirect",
                  "type": "string"
                },
                "expiration_date": {
                  "description": "The expiration date of the insider trade.",
                  "example": "2023-12-06",
                  "title": "Insider Expiration Date",
                  "type": "string"
                },
                "filing_date": {
                  "description": "The filing date of the insider trade.",
                  "example": "2023-12-06",
                  "title": "Insider Filing Date",
                  "type": "string"
                },
                "formtype": {
                  "description": "The SEC form the row came from: 3 (initial ownership), 4 (change in ownership), 5 (annual), 144 (notice of intended sale, not an executed trade), each with an /A variant for amendments.",
                  "enum": [
                    "3",
                    "3/A",
                    "4",
                    "4/A",
                    "5",
                    "5/A",
                    "144",
                    "144/A"
                  ],
                  "example": "4",
                  "title": "Insider Form Type",
                  "type": "string"
                },
                "ids": {
                  "description": "The IDs of the insider trade.",
                  "example": [
                    "1234"
                  ],
                  "items": {
                    "type": "string"
                  },
                  "title": "Insider IDs",
                  "type": "array"
                },
                "is_10b5_1": {
                  "description": "True if this insider trade was part of a 10b5-1 plan",
                  "example": true,
                  "title": "Insider Is 10b5-1",
                  "type": "boolean"
                },
                "is_director": {
                  "description": "Whether the insider is a director.",
                  "example": true,
                  "title": "Insider Is Director",
                  "type": "boolean"
                },
                "is_officer": {
                  "description": "Whether the insider is an officer.",
                  "example": true,
                  "title": "Insider Is Officer",
                  "type": "boolean"
                },
                "is_ten_percent_owner": {
                  "description": "Whether the insider is a 10% owner.",
                  "example": true,
                  "title": "Insider Is 10 Owner",
                  "type": "boolean"
                },
                "issuer_cik": {
                  "description": "SEC Central Index Key of the issuing company.",
                  "example": "0001326801",
                  "title": "Issuer CIK",
                  "type": "string"
                },
                "natureofownership": {
                  "description": "The nature of ownership of the insider trade.",
                  "example": "Direct",
                  "title": "Insider Nature of Ownership",
                  "type": "string"
                },
                "officer_title": {
                  "description": "The officer title of the insider trade.",
                  "example": "CEO",
                  "title": "Insider Officer Title",
                  "type": "string"
                },
                "owner_name": {
                  "description": "The owner name of the insider trade.",
                  "example": "John Doe",
                  "title": "Insider Owner Name",
                  "type": "string"
                },
                "price": {
                  "description": "The price of the insider trade.",
                  "example": "123.45",
                  "title": "Insider Price",
                  "type": "string"
                },
                "price_excercisable": {
                  "description": "The price excercisable of the insider trade.",
                  "example": "123.45",
                  "title": "Insider Price Excercisable",
                  "type": "string"
                },
                "reporter_cik": {
                  "description": "SEC Central Index Key of the reporting owner. Stable across issuers and over time, so use it rather than owner_name to tie one insider's filings together.",
                  "example": "0001548760",
                  "title": "Reporter CIK",
                  "type": "string"
                },
                "security_ad_code": {
                  "description": "The security AD code of the insider trade.",
                  "example": "1234",
                  "title": "Insider Security AD Code",
                  "type": "string"
                },
                "security_title": {
                  "description": "The security title of the insider trade.",
                  "example": "Common Stock",
                  "title": "Insider Security Title",
                  "type": "string"
                },
                "shares_owned_after": {
                  "description": "The number of shares owned after the insider trade.",
                  "example": 2000,
                  "title": "Insider Shares Owned After",
                  "type": "integer"
                },
                "shares_owned_before": {
                  "description": "The number of shares owned before the insider trade.",
                  "example": 1000,
                  "title": "Insider Shares Owned Before",
                  "type": "integer"
                },
                "ticker": {
                  "description": "The stock ticker.",
                  "example": "AAPL",
                  "title": "Stock Ticker",
                  "type": "string"
                },
                "transaction_code": {
                  "description": "The transaction code of the insider trade.",
                  "example": "S",
                  "title": "Insider Transaction Code",
                  "type": "string"
                },
                "transaction_date": {
                  "description": "The transaction date of the insider trade.",
                  "example": "2023-12-06",
                  "title": "Insider Transaction Date",
                  "type": "string"
                },
                "transactions": {
                  "description": "The number of transactions of the insider trade.",
                  "example": 1,
                  "title": "Insider Transactions",
                  "type": "integer"
                }
              },
              "title": "Insider Trade Agg",
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
    "summary": "Transactions",
    "tags": [
      "insiders"
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

## GET /api/insider/{sector}/sector-flow

Sector Flow

Returns an aggregated view of the insider flow for the given sector.

This can be used to quickly examine the buy & sell insider flow for a given trading date


### Fully resolved operation
```json
{
  "key": "GET /api/insider/{sector}/sector-flow",
  "method": "GET",
  "path": "/api/insider/{sector}/sector-flow",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "Returns an aggregated view of the insider flow for the given sector.\n\nThis can be used to quickly examine the buy & sell insider flow for a given trading date\n",
    "operationId": "PublicApi.InsiderController.sector_flow",
    "parameters": [
      {
        "description": "",
        "in": "path",
        "name": "sector",
        "required": true,
        "schema": {
          "description": "A financial sector.",
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
          "title": "Sector",
          "type": "string"
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
      },
      {
        "description": "",
        "in": "query",
        "name": "page",
        "required": false,
        "schema": {
          "description": "Page number (use with limit). Starts on page 0.",
          "example": 1,
          "title": "Page",
          "type": "integer"
        }
      }
    ],
    "responses": {
      "200": {
        "content": {
          "application/json": {
            "schema": {
              "description": "The total buy/sell insider flow for a given sector on a given date. If there have been buy & sells on the same day then there will be 2 rows for that day.",
              "example": {
                "data": [
                  {
                    "avg_price": 162.32,
                    "buy_sell": "sell",
                    "date": "2024-12-12",
                    "premium": "664386",
                    "transactions": 54,
                    "uniq_insiders": 10,
                    "volume": 244331
                  }
                ],
                "has_more": false
              },
              "properties": {
                "avg_price": {
                  "description": "The average price of the insider trade.",
                  "example": "123.45",
                  "title": "Insider Average Price",
                  "type": "string"
                },
                "buy_sell": {
                  "description": "Whether the insider bought or sold.",
                  "enum": [
                    "buy",
                    "sell"
                  ],
                  "example": "buy",
                  "title": "Transaction Side",
                  "type": "string"
                },
                "date": {
                  "description": "A trading date in ISO format.\n",
                  "example": "2023-09-08",
                  "title": "Market General Trading day",
                  "type": "string"
                },
                "has_more": {
                  "description": "Indicates whether there are more results available beyond the current page.",
                  "example": false,
                  "title": "Has More",
                  "type": "boolean"
                },
                "premium": {
                  "description": "The premium of the insider trade.",
                  "example": "123.45",
                  "title": "Insider Premium",
                  "type": "string"
                },
                "transactions": {
                  "description": "The number of transactions of the insider trade.",
                  "example": 1,
                  "title": "Insider Transactions",
                  "type": "integer"
                },
                "uniq_insiders": {
                  "description": "The number of unique insiders of the insider trade.",
                  "example": 1,
                  "title": "Insider Unique Insiders",
                  "type": "integer"
                },
                "volume": {
                  "description": "The volume of the insider trade.",
                  "example": 1000,
                  "title": "Insider Volume",
                  "type": "integer"
                }
              },
              "title": "Insider Sector Flow",
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
    "summary": "Sector Flow",
    "tags": [
      "insiders"
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

## GET /api/insider/{ticker}

Insiders

Returns all insiders for the given ticker


### Fully resolved operation
```json
{
  "key": "GET /api/insider/{ticker}",
  "method": "GET",
  "path": "/api/insider/{ticker}",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "Returns all insiders for the given ticker\n",
    "operationId": "PublicApi.InsiderController.insiders",
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
              "description": "An insider",
              "example": {
                "data": [
                  {
                    "cik": "0001823951",
                    "display_name": "KARP ALEXANDER",
                    "id": 10343,
                    "is_person": true,
                    "logo_url": "https://storage.googleapis.com/uwassets/insiders/10343",
                    "name": "KARP ALEXANDER",
                    "name_slug": "karp-alexander",
                    "ticker": "PLTR"
                  }
                ]
              },
              "properties": {
                "cik": {
                  "description": "The insider's CIK (Central Index Key).",
                  "example": "0000902015",
                  "title": "Insider CIK",
                  "type": "string"
                },
                "id": {
                  "description": "The insider's ID.",
                  "example": 1,
                  "title": "Insider ID",
                  "type": "integer"
                },
                "is_person": {
                  "description": "Whether the insider is a person. False if the insider is a fund, LLC, etc.",
                  "example": true,
                  "title": "Insider Is Person",
                  "type": "boolean"
                },
                "logo_url": {
                  "description": "The URL to the insider's logo.",
                  "example": "https://example.com/logo.png",
                  "title": "Insider Logo URL",
                  "type": "string"
                },
                "name": {
                  "description": "The name of the insider.",
                  "example": "John Doe",
                  "title": "Insider Name",
                  "type": "string"
                },
                "name_slug": {
                  "description": "The slugified name of the insider.",
                  "example": "john-doe",
                  "title": "Insider Name Slug",
                  "type": "string"
                },
                "social_links": {
                  "description": "The social links of the insider.",
                  "example": [
                    "https://twitter.com/johndoe"
                  ],
                  "items": {
                    "type": "string"
                  },
                  "title": "Insider Social Links",
                  "type": "array"
                },
                "ticker": {
                  "description": "The stock ticker.",
                  "example": "AAPL",
                  "title": "Stock Ticker",
                  "type": "string"
                }
              },
              "title": "Insider",
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
    "summary": "Insiders",
    "tags": [
      "insiders"
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

## GET /api/insider/{ticker}/ticker-flow

Ticker Flow

Returns an aggregated view of the insider flow for the given ticker.

This can be used to quickly examine the buy & sell insider flow for a given trading date


### Fully resolved operation
```json
{
  "key": "GET /api/insider/{ticker}/ticker-flow",
  "method": "GET",
  "path": "/api/insider/{ticker}/ticker-flow",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "Returns an aggregated view of the insider flow for the given ticker.\n\nThis can be used to quickly examine the buy & sell insider flow for a given trading date\n",
    "operationId": "PublicApi.InsiderController.ticker_flow",
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
      },
      {
        "description": "",
        "in": "query",
        "name": "page",
        "required": false,
        "schema": {
          "description": "Page number (use with limit). Starts on page 0.",
          "example": 1,
          "title": "Page",
          "type": "integer"
        }
      }
    ],
    "responses": {
      "200": {
        "content": {
          "application/json": {
            "schema": {
              "description": "The total buy/sell insider flow for a given ticker on a given date. If there have been buy & sells on the same day then there will be 2 rows for that day.",
              "example": {
                "data": [
                  {
                    "avg_price": 162.32,
                    "buy_sell": "sell",
                    "date": "2024-12-12",
                    "premium": "664386",
                    "transactions": 54,
                    "uniq_insiders": 10,
                    "volume": 244331
                  }
                ],
                "has_more": false
              },
              "properties": {
                "avg_price": {
                  "description": "The average price of the insider trade.",
                  "example": "123.45",
                  "title": "Insider Average Price",
                  "type": "string"
                },
                "buy_sell": {
                  "description": "Whether the insider bought or sold.",
                  "enum": [
                    "buy",
                    "sell"
                  ],
                  "example": "buy",
                  "title": "Transaction Side",
                  "type": "string"
                },
                "date": {
                  "description": "A trading date in ISO format.\n",
                  "example": "2023-09-08",
                  "title": "Market General Trading day",
                  "type": "string"
                },
                "has_more": {
                  "description": "Indicates whether there are more results available beyond the current page.",
                  "example": false,
                  "title": "Has More",
                  "type": "boolean"
                },
                "premium": {
                  "description": "The premium of the insider trade.",
                  "example": "123.45",
                  "title": "Insider Premium",
                  "type": "string"
                },
                "transactions": {
                  "description": "The number of transactions of the insider trade.",
                  "example": 1,
                  "title": "Insider Transactions",
                  "type": "integer"
                },
                "uniq_insiders": {
                  "description": "The number of unique insiders of the insider trade.",
                  "example": 1,
                  "title": "Insider Unique Insiders",
                  "type": "integer"
                },
                "volume": {
                  "description": "The volume of the insider trade.",
                  "example": 1000,
                  "title": "Insider Volume",
                  "type": "integer"
                }
              },
              "title": "Insider Ticker Flow",
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
    "summary": "Ticker Flow",
    "tags": [
      "insiders"
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
