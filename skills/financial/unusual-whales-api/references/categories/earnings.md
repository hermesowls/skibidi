# earnings

Source: https://api.unusualwhales.com/docs/openapi.yaml; retrieved 2026-09-24T01:21:27.462441+00:00

Full descriptions, inherited security, effective parameters, responses and schemas. No live calls.

## GET /api/earnings/afterhours

Afterhours

Returns the afterhours earnings for a given date.

If you are looking to scan for extreme IV term steepness before earnings use https://unusualwhales.com/skills/uw-earnings-vol-scan-skill.md


### Fully resolved operation
```json
{
  "key": "GET /api/earnings/afterhours",
  "method": "GET",
  "path": "/api/earnings/afterhours",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "Returns the afterhours earnings for a given date.\n\nIf you are looking to scan for extreme IV term steepness before earnings use https://unusualwhales.com/skills/uw-earnings-vol-scan-skill.md\n",
    "operationId": "PublicApi.EarningsController.afterhours",
    "parameters": [
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
        "name": "limit",
        "required": false,
        "schema": {
          "default": 50,
          "description": "How many items to return. Default: 50. Max: 100. Min: 1.",
          "example": 10,
          "maximum": 100,
          "minimum": 1,
          "title": "Default 50 Max 100 Min 1",
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
              "description": "The earnings data for a date and report time.\n",
              "example": {
                "data": [
                  {
                    "actual_eps": "2.45",
                    "continent": "North America",
                    "country_code": "US",
                    "country_name": "UNITED STATES",
                    "ending_fiscal_quarter": "2022-12-31",
                    "expected_move": "9.91",
                    "expected_move_perc": "0.0359",
                    "full_name": "INVENTRUST PROPERTIES",
                    "has_options": true,
                    "is_s_p_500": false,
                    "marketcap": "1649115201",
                    "post_earnings_close": "148.42",
                    "post_earnings_date": "2023-02-14",
                    "pre_earnings_close": "143.23",
                    "pre_earnings_date": "2023-02-13",
                    "reaction": "0.041",
                    "report_date": "2023-02-14",
                    "report_time": "postmarket",
                    "sector": "Real Estate",
                    "source": "company",
                    "street_mean_est": "2.25",
                    "symbol": "IVT"
                  },
                  {
                    "actual_eps": "2.45",
                    "continent": "Europe",
                    "country_code": "LU",
                    "country_name": "LUXEMBOURG",
                    "ending_fiscal_quarter": "2022-12-31",
                    "expected_move": "9.91",
                    "expected_move_perc": "0.0359",
                    "full_name": "TERNIUM SA",
                    "has_options": true,
                    "is_s_p_500": false,
                    "marketcap": "7375279462",
                    "post_earnings_close": "148.42",
                    "post_earnings_date": "2023-02-14",
                    "pre_earnings_close": "143.23",
                    "pre_earnings_date": "2023-02-13",
                    "reaction": "0.041",
                    "report_date": "2023-02-14",
                    "report_time": "postmarket",
                    "sector": "Basic Materials",
                    "source": "company",
                    "street_mean_est": "2.25",
                    "symbol": "TX"
                  }
                ]
              },
              "properties": {
                "actual_eps": {
                  "description": "",
                  "example": "1.44",
                  "title": "Actual EPS",
                  "type": "string"
                },
                "continent": {
                  "description": "",
                  "example": "North America",
                  "title": "Continent",
                  "type": "string"
                },
                "country_code": {
                  "description": "",
                  "example": "US",
                  "title": "Country Code",
                  "type": "string"
                },
                "country_name": {
                  "description": "",
                  "example": "UNITED STATES",
                  "title": "Country Name",
                  "type": "string"
                },
                "ending_fiscal_quarter": {
                  "description": "An ISO date.",
                  "example": "2024-01-09",
                  "title": "General ISO Date",
                  "type": "string"
                },
                "expected_move": {
                  "description": "The expected earnings move in $.",
                  "example": "1.23",
                  "title": "Expected Move",
                  "type": "string"
                },
                "expected_move_perc": {
                  "description": "The expected earnings move in %.",
                  "example": "0.08",
                  "title": "Expected Move Perc",
                  "type": "string"
                },
                "full_name": {
                  "description": "",
                  "example": "MICROSOFT CORP",
                  "title": "Full Name",
                  "type": "string"
                },
                "has_options": {
                  "description": "Whether the company has options available for trading",
                  "example": true,
                  "nullable": true,
                  "title": "Has Options",
                  "type": "boolean"
                },
                "is_s_p_500": {
                  "description": "",
                  "title": "Is Part of the S&P 500",
                  "type": "boolean"
                },
                "marketcap": {
                  "description": "",
                  "example": "152983052",
                  "title": "Marketcap",
                  "type": "string"
                },
                "post_earnings_close": {
                  "description": "The close stock price of the ticker.",
                  "example": "182.91",
                  "title": "Stock Close Price",
                  "type": "string"
                },
                "post_earnings_date": {
                  "description": "An ISO date.",
                  "example": "2024-01-09",
                  "title": "General ISO Date",
                  "type": "string"
                },
                "pre_earnings_close": {
                  "description": "The close stock price of the ticker.",
                  "example": "182.91",
                  "title": "Stock Close Price",
                  "type": "string"
                },
                "pre_earnings_date": {
                  "description": "An ISO date.",
                  "example": "2024-01-09",
                  "title": "General ISO Date",
                  "type": "string"
                },
                "reaction": {
                  "description": "The 1D % stock move after the earnings report.",
                  "example": "0.15",
                  "title": "Reaction",
                  "type": "string"
                },
                "report_date": {
                  "description": "An ISO date.",
                  "example": "2024-01-09",
                  "title": "General ISO Date",
                  "type": "string"
                },
                "report_time": {
                  "description": "The earnings report time. Possible values include: premarket, postmarket and unknown",
                  "example": "postmarket",
                  "title": "Report Time",
                  "type": "string"
                },
                "sector": {
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
                },
                "source": {
                  "description": "The source of the report date. Either the report date comes from the company or it is an estimation. Possible values: company, estimation.",
                  "example": "company",
                  "title": "Source",
                  "type": "string"
                },
                "street_mean_est": {
                  "description": "The Street mean EPS estimates.",
                  "example": "1.34",
                  "title": "Street Mean Est",
                  "type": "string"
                },
                "symbol": {
                  "description": "",
                  "example": "MSFT",
                  "title": "Ticker Symbol",
                  "type": "string"
                }
              },
              "title": "Earnings",
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
    "summary": "Afterhours",
    "tags": [
      "earnings"
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

## GET /api/earnings/premarket

Premarket

Returns the premarket earnings for a given date.

If you are looking to scan for extreme IV term steepness before earnings use https://unusualwhales.com/skills/uw-earnings-vol-scan-skill.md


### Fully resolved operation
```json
{
  "key": "GET /api/earnings/premarket",
  "method": "GET",
  "path": "/api/earnings/premarket",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "Returns the premarket earnings for a given date.\n\nIf you are looking to scan for extreme IV term steepness before earnings use https://unusualwhales.com/skills/uw-earnings-vol-scan-skill.md\n",
    "operationId": "PublicApi.EarningsController.premarket",
    "parameters": [
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
        "name": "limit",
        "required": false,
        "schema": {
          "default": 50,
          "description": "How many items to return. Default: 50. Max: 100. Min: 1.",
          "example": 10,
          "maximum": 100,
          "minimum": 1,
          "title": "Default 50 Max 100 Min 1",
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
              "description": "The earnings data for a date and report time.\n",
              "example": {
                "data": [
                  {
                    "actual_eps": "2.45",
                    "continent": "North America",
                    "country_code": "US",
                    "country_name": "UNITED STATES",
                    "ending_fiscal_quarter": "2022-12-31",
                    "expected_move": "9.91",
                    "expected_move_perc": "0.0359",
                    "full_name": "INVENTRUST PROPERTIES",
                    "has_options": true,
                    "is_s_p_500": false,
                    "marketcap": "1649115201",
                    "post_earnings_close": "148.42",
                    "post_earnings_date": "2023-02-14",
                    "pre_earnings_close": "143.23",
                    "pre_earnings_date": "2023-02-13",
                    "reaction": "0.041",
                    "report_date": "2023-02-14",
                    "report_time": "postmarket",
                    "sector": "Real Estate",
                    "source": "company",
                    "street_mean_est": "2.25",
                    "symbol": "IVT"
                  },
                  {
                    "actual_eps": "2.45",
                    "continent": "Europe",
                    "country_code": "LU",
                    "country_name": "LUXEMBOURG",
                    "ending_fiscal_quarter": "2022-12-31",
                    "expected_move": "9.91",
                    "expected_move_perc": "0.0359",
                    "full_name": "TERNIUM SA",
                    "has_options": true,
                    "is_s_p_500": false,
                    "marketcap": "7375279462",
                    "post_earnings_close": "148.42",
                    "post_earnings_date": "2023-02-14",
                    "pre_earnings_close": "143.23",
                    "pre_earnings_date": "2023-02-13",
                    "reaction": "0.041",
                    "report_date": "2023-02-14",
                    "report_time": "postmarket",
                    "sector": "Basic Materials",
                    "source": "company",
                    "street_mean_est": "2.25",
                    "symbol": "TX"
                  }
                ]
              },
              "properties": {
                "actual_eps": {
                  "description": "",
                  "example": "1.44",
                  "title": "Actual EPS",
                  "type": "string"
                },
                "continent": {
                  "description": "",
                  "example": "North America",
                  "title": "Continent",
                  "type": "string"
                },
                "country_code": {
                  "description": "",
                  "example": "US",
                  "title": "Country Code",
                  "type": "string"
                },
                "country_name": {
                  "description": "",
                  "example": "UNITED STATES",
                  "title": "Country Name",
                  "type": "string"
                },
                "ending_fiscal_quarter": {
                  "description": "An ISO date.",
                  "example": "2024-01-09",
                  "title": "General ISO Date",
                  "type": "string"
                },
                "expected_move": {
                  "description": "The expected earnings move in $.",
                  "example": "1.23",
                  "title": "Expected Move",
                  "type": "string"
                },
                "expected_move_perc": {
                  "description": "The expected earnings move in %.",
                  "example": "0.08",
                  "title": "Expected Move Perc",
                  "type": "string"
                },
                "full_name": {
                  "description": "",
                  "example": "MICROSOFT CORP",
                  "title": "Full Name",
                  "type": "string"
                },
                "has_options": {
                  "description": "Whether the company has options available for trading",
                  "example": true,
                  "nullable": true,
                  "title": "Has Options",
                  "type": "boolean"
                },
                "is_s_p_500": {
                  "description": "",
                  "title": "Is Part of the S&P 500",
                  "type": "boolean"
                },
                "marketcap": {
                  "description": "",
                  "example": "152983052",
                  "title": "Marketcap",
                  "type": "string"
                },
                "post_earnings_close": {
                  "description": "The close stock price of the ticker.",
                  "example": "182.91",
                  "title": "Stock Close Price",
                  "type": "string"
                },
                "post_earnings_date": {
                  "description": "An ISO date.",
                  "example": "2024-01-09",
                  "title": "General ISO Date",
                  "type": "string"
                },
                "pre_earnings_close": {
                  "description": "The close stock price of the ticker.",
                  "example": "182.91",
                  "title": "Stock Close Price",
                  "type": "string"
                },
                "pre_earnings_date": {
                  "description": "An ISO date.",
                  "example": "2024-01-09",
                  "title": "General ISO Date",
                  "type": "string"
                },
                "reaction": {
                  "description": "The 1D % stock move after the earnings report.",
                  "example": "0.15",
                  "title": "Reaction",
                  "type": "string"
                },
                "report_date": {
                  "description": "An ISO date.",
                  "example": "2024-01-09",
                  "title": "General ISO Date",
                  "type": "string"
                },
                "report_time": {
                  "description": "The earnings report time. Possible values include: premarket, postmarket and unknown",
                  "example": "postmarket",
                  "title": "Report Time",
                  "type": "string"
                },
                "sector": {
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
                },
                "source": {
                  "description": "The source of the report date. Either the report date comes from the company or it is an estimation. Possible values: company, estimation.",
                  "example": "company",
                  "title": "Source",
                  "type": "string"
                },
                "street_mean_est": {
                  "description": "The Street mean EPS estimates.",
                  "example": "1.34",
                  "title": "Street Mean Est",
                  "type": "string"
                },
                "symbol": {
                  "description": "",
                  "example": "MSFT",
                  "title": "Ticker Symbol",
                  "type": "string"
                }
              },
              "title": "Earnings",
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
    "summary": "Premarket",
    "tags": [
      "earnings"
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

## GET /api/earnings/{ticker}

Historical Ticker Earnings

Returns the historical earnings for the given ticker.

The returned data includes information about how the stock
performed before and after the earnings event in its history.

Furthermore, data about how a long and short straddle would have performed
in the past are included as well.

If you are looking to scan for extreme IV term steepness before earnings use https://unusualwhales.com/skills/uw-earnings-vol-scan-skill.md


### Fully resolved operation
```json
{
  "key": "GET /api/earnings/{ticker}",
  "method": "GET",
  "path": "/api/earnings/{ticker}",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "Returns the historical earnings for the given ticker.\n\nThe returned data includes information about how the stock\nperformed before and after the earnings event in its history.\n\nFurthermore, data about how a long and short straddle would have performed\nin the past are included as well.\n\nIf you are looking to scan for extreme IV term steepness before earnings use https://unusualwhales.com/skills/uw-earnings-vol-scan-skill.md\n",
    "operationId": "PublicApi.EarningsController.ticker",
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
              "description": "The earnings data for a ticker and date.\n",
              "example": {
                "data": [
                  {
                    "actual_eps": "2.45",
                    "ending_fiscal_quarter": "2024-09-30",
                    "expected_move": "9.91",
                    "expected_move_perc": "0.0359",
                    "long_straddle_1d": "0.2349",
                    "long_straddle_1w": "0.0129",
                    "post_earnings_move_1d": "0.0724",
                    "post_earnings_move_1w": "0.132",
                    "post_earnings_move_2w": "0.1582",
                    "post_earnings_move_3d": "0.0231",
                    "pre_earnings_move_1d": "0.0724",
                    "pre_earnings_move_1w": "0.132",
                    "pre_earnings_move_2w": "0.1582",
                    "pre_earnings_move_3d": "0.0231",
                    "report_date": "2024-11-10",
                    "report_time": "postmarket",
                    "short_straddle_1d": "-0.5830",
                    "short_straddle_1w": "-0.005",
                    "source": "company",
                    "street_mean_est": "2.25"
                  },
                  {
                    "actual_eps": "2.32",
                    "ending_fiscal_quarter": "2024-06-30",
                    "expected_move": "8.23",
                    "expected_move_perc": "0.0261",
                    "long_straddle_1d": "0.2349",
                    "long_straddle_1w": "0.0129",
                    "post_earnings_move_1d": "0.0724",
                    "post_earnings_move_1w": "0.132",
                    "post_earnings_move_2w": "0.1582",
                    "post_earnings_move_3d": "0.0231",
                    "pre_earnings_move_1d": "0.0724",
                    "pre_earnings_move_1w": "0.132",
                    "pre_earnings_move_2w": "0.1582",
                    "pre_earnings_move_3d": "0.0231",
                    "report_date": "2024-08-02",
                    "report_time": "postmarket",
                    "short_straddle_1d": "-0.5830",
                    "short_straddle_1w": "-0.005",
                    "source": "company",
                    "street_mean_est": "2.15"
                  }
                ]
              },
              "properties": {
                "actual_eps": {
                  "description": "",
                  "example": "1.44",
                  "title": "Actual EPS",
                  "type": "string"
                },
                "ending_fiscal_quarter": {
                  "description": "An ISO date.",
                  "example": "2024-01-09",
                  "title": "General ISO Date",
                  "type": "string"
                },
                "expected_move": {
                  "description": "The expected earnings move in $.",
                  "example": "1.23",
                  "title": "Expected Move",
                  "type": "string"
                },
                "expected_move_perc": {
                  "description": "The expected earnings move in %.",
                  "example": "0.08",
                  "title": "Expected Move Perc",
                  "type": "string"
                },
                "long_straddle_1d": {
                  "description": "The 1 day % returns for the closest expiry long ATM straddle. The straddle expiry is equal to or greater than 1 day after earnings.",
                  "example": "0.3421",
                  "title": "Long Straddle 1 Day",
                  "type": "string"
                },
                "long_straddle_1w": {
                  "description": "The 1 week % returns for the closest expiry long ATM straddle. The straddle expiry is equal to or greater than 1 week after earnings.",
                  "example": "0.3421",
                  "title": "Long Straddle 1 Week",
                  "type": "string"
                },
                "post_earnings_move_1d": {
                  "description": "The 1 day % move after the earnings report.",
                  "example": "0.08",
                  "title": "Post Earnings Move 1 Day",
                  "type": "string"
                },
                "post_earnings_move_1w": {
                  "description": "The 1 week % move after the earnings report.",
                  "example": "0.08",
                  "title": "Post Earnings Move 1 Week",
                  "type": "string"
                },
                "post_earnings_move_2w": {
                  "description": "The 2 week % move after the earnings report.",
                  "example": "0.08",
                  "title": "Post Earnings Move 2 Week",
                  "type": "string"
                },
                "post_earnings_move_3d": {
                  "description": "The 3 day % move after the earnings report.",
                  "example": "0.08",
                  "title": "Post Earnings Move 13Day",
                  "type": "string"
                },
                "pre_earnings_move_1d": {
                  "description": "The 1 day % move up to the earnings report.",
                  "example": "0.08",
                  "title": "Pre Earnings Move 1 Day",
                  "type": "string"
                },
                "pre_earnings_move_1w": {
                  "description": "The 1 week % move up to the earnings report.",
                  "example": "0.08",
                  "title": "Pre Earnings Move 1 Week",
                  "type": "string"
                },
                "pre_earnings_move_2w": {
                  "description": "The 2 week % move up to the earnings report.",
                  "example": "0.08",
                  "title": "Pre Earnings Move 2 Week",
                  "type": "string"
                },
                "pre_earnings_move_3d": {
                  "description": "The 3 day % move up to the earnings report.",
                  "example": "0.08",
                  "title": "Pre Earnings Move 13Day",
                  "type": "string"
                },
                "report_date": {
                  "description": "An ISO date.",
                  "example": "2024-01-09",
                  "title": "General ISO Date",
                  "type": "string"
                },
                "report_time": {
                  "description": "The earnings report time. Possible values include: premarket, postmarket and unknown",
                  "example": "postmarket",
                  "title": "Report Time",
                  "type": "string"
                },
                "short_straddle_1d": {
                  "description": "The 1 day % returns for the closest expiry short ATM straddle. The straddle expiry is equal to or greater than 1 day after earnings.",
                  "example": "0.3421",
                  "title": "Short Straddle 1 Day",
                  "type": "string"
                },
                "short_straddle_1w": {
                  "description": "The 1 week % returns for the closest expiry short ATM straddle. The straddle expiry is equal to or greater than 1 week after earnings.",
                  "example": "0.3421",
                  "title": "Short Straddle 1 Week",
                  "type": "string"
                },
                "source": {
                  "description": "The source of the report date. Either the report date comes from the company or it is an estimation. Possible values: company, estimation.",
                  "example": "company",
                  "title": "Source",
                  "type": "string"
                },
                "street_mean_est": {
                  "description": "The Street mean EPS estimates.",
                  "example": "1.34",
                  "title": "Street Mean Est",
                  "type": "string"
                }
              },
              "title": "Historical Ticker Earnings",
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
    "summary": "Historical Ticker Earnings",
    "tags": [
      "earnings"
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
