# economy

Source: https://api.unusualwhales.com/docs/openapi.yaml; retrieved 2026-09-24T01:21:27.462441+00:00

Full descriptions, inherited security, effective parameters, responses and schemas. No live calls.

## GET /api/economy/{indicator}

Economic Indicator

**Requires Advanced+ tier (Advanced, Enterprise, or Enterprise + Kafka).**

Returns a long-running US economic indicator series.

Indicators: gdp, gdp-per-capita, treasury-yield, fed-funds, cpi, inflation, retail-sales, durables, unemployment, payrolls.

The optional `interval` and `maturity` parameters apply only to indicators that support them
(e.g. `treasury-yield` accepts a maturity like `10year`).


### Fully resolved operation
```json
{
  "key": "GET /api/economy/{indicator}",
  "method": "GET",
  "path": "/api/economy/{indicator}",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "**Requires Advanced+ tier (Advanced, Enterprise, or Enterprise + Kafka).**\n\nReturns a long-running US economic indicator series.\n\nIndicators: gdp, gdp-per-capita, treasury-yield, fed-funds, cpi, inflation, retail-sales, durables, unemployment, payrolls.\n\nThe optional `interval` and `maturity` parameters apply only to indicators that support them\n(e.g. `treasury-yield` accepts a maturity like `10year`).\n",
    "operationId": "PublicApi.EconomyController.show",
    "parameters": [
      {
        "description": "",
        "in": "path",
        "name": "indicator",
        "required": true,
        "schema": {
          "enum": [
            "gdp",
            "gdp-per-capita",
            "treasury-yield",
            "fed-funds",
            "cpi",
            "inflation",
            "retail-sales",
            "durables",
            "unemployment",
            "payrolls"
          ],
          "type": "string"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "interval",
        "required": false,
        "schema": {
          "enum": [
            "daily",
            "weekly",
            "monthly",
            "quarterly",
            "annual",
            "semiannual"
          ],
          "type": "string"
        }
      },
      {
        "description": "Only for treasury-yield.",
        "in": "query",
        "name": "maturity",
        "required": false,
        "schema": {
          "enum": [
            "3month",
            "2year",
            "5year",
            "7year",
            "10year",
            "30year"
          ],
          "type": "string"
        }
      }
    ],
    "responses": {
      "200": {
        "content": {
          "application/json": {
            "schema": {
              "properties": {
                "data": {
                  "properties": {
                    "data": {
                      "items": {
                        "properties": {
                          "date": {
                            "format": "date",
                            "nullable": true,
                            "type": "string"
                          },
                          "value": {
                            "nullable": true,
                            "type": "number"
                          }
                        },
                        "title": "Series Point",
                        "type": "object"
                      },
                      "type": "array"
                    },
                    "interval": {
                      "nullable": true,
                      "type": "string"
                    },
                    "name": {
                      "nullable": true,
                      "type": "string"
                    },
                    "unit": {
                      "nullable": true,
                      "type": "string"
                    }
                  },
                  "title": "Macro Series",
                  "type": "object"
                }
              },
              "title": "Macro Series Response",
              "type": "object"
            }
          }
        },
        "description": "Economic Series"
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
    "summary": "Economic Indicator",
    "tags": [
      "economy"
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
