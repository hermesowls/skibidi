# intel

Source: https://api.unusualwhales.com/docs/openapi.yaml; retrieved 2026-09-24T01:21:27.462441+00:00

Full descriptions, inherited security, effective parameters, responses and schemas. No live calls.

## GET /api/analytics/sliding

Sliding-Window Analytics

**Requires Advanced+ tier (Advanced, Enterprise, or Enterprise + Kafka).** Sliding window statistical analytics across one or more tickers.

### Fully resolved operation
```json
{
  "key": "GET /api/analytics/sliding",
  "method": "GET",
  "path": "/api/analytics/sliding",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "**Requires Advanced+ tier (Advanced, Enterprise, or Enterprise + Kafka).** Sliding window statistical analytics across one or more tickers.",
    "operationId": "PublicApi.IntelController.analytics_sliding",
    "parameters": [
      {
        "description": "",
        "in": "query",
        "name": "symbols",
        "required": true,
        "schema": {
          "type": "string"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "range",
        "required": true,
        "schema": {
          "type": "string"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "range_end",
        "required": false,
        "schema": {
          "type": "string"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "interval",
        "required": false,
        "schema": {
          "default": "DAILY",
          "type": "string"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "ohlc",
        "required": false,
        "schema": {
          "default": "close",
          "type": "string"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "window_size",
        "required": false,
        "schema": {
          "default": 20,
          "minimum": 1,
          "type": "integer"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "calculations",
        "required": true,
        "schema": {
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
                    "meta": {
                      "nullable": true,
                      "type": "object"
                    },
                    "payload": {
                      "nullable": true,
                      "type": "object"
                    }
                  },
                  "type": "object"
                }
              },
              "title": "Analytics Response",
              "type": "object"
            }
          }
        },
        "description": "Analytics Sliding"
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
    "summary": "Sliding-Window Analytics",
    "tags": [
      "intel"
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

## GET /api/analytics/window

Fixed-Window Analytics

**Requires Advanced+ tier (Advanced, Enterprise, or Enterprise + Kafka).** Statistical analytics over a fixed window across one or more tickers. Returns mean, stddev, correlation, etc.

### Fully resolved operation
```json
{
  "key": "GET /api/analytics/window",
  "method": "GET",
  "path": "/api/analytics/window",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "**Requires Advanced+ tier (Advanced, Enterprise, or Enterprise + Kafka).** Statistical analytics over a fixed window across one or more tickers. Returns mean, stddev, correlation, etc.",
    "operationId": "PublicApi.IntelController.analytics_window",
    "parameters": [
      {
        "description": "Comma-separated tickers.",
        "in": "query",
        "name": "symbols",
        "required": true,
        "schema": {
          "example": "AAPL,IBM,MSFT",
          "type": "string"
        }
      },
      {
        "description": "Either an ISO date for the start of the window (pair with the optional range_end) or a relative shorthand like '2month' or 'full'.",
        "in": "query",
        "name": "range",
        "required": true,
        "schema": {
          "example": "2month",
          "type": "string"
        }
      },
      {
        "description": "Optional end date when using ISO range_start.",
        "in": "query",
        "name": "range_end",
        "required": false,
        "schema": {
          "example": "2024-08-31",
          "type": "string"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "interval",
        "required": false,
        "schema": {
          "default": "DAILY",
          "enum": [
            "1min",
            "5min",
            "15min",
            "30min",
            "60min",
            "DAILY",
            "WEEKLY",
            "MONTHLY"
          ],
          "type": "string"
        }
      },
      {
        "description": "",
        "in": "query",
        "name": "ohlc",
        "required": false,
        "schema": {
          "default": "close",
          "enum": [
            "open",
            "high",
            "low",
            "close"
          ],
          "type": "string"
        }
      },
      {
        "description": "Comma-separated. Supported: MIN, MAX, MEAN, MEDIAN, CUMULATIVE_RETURN, VARIANCE, STDDEV, MAX_DRAWDOWN, HISTOGRAM, AUTOCORRELATION, COVARIANCE, CORRELATION.",
        "in": "query",
        "name": "calculations",
        "required": true,
        "schema": {
          "example": "MEAN,STDDEV,CORRELATION",
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
                    "meta": {
                      "nullable": true,
                      "type": "object"
                    },
                    "payload": {
                      "nullable": true,
                      "type": "object"
                    }
                  },
                  "type": "object"
                }
              },
              "title": "Analytics Response",
              "type": "object"
            }
          }
        },
        "description": "Analytics Window"
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
    "summary": "Fixed-Window Analytics",
    "tags": [
      "intel"
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

## GET /api/calendar/ipo

IPO Calendar

**Requires Advanced+ tier (Advanced, Enterprise, or Enterprise + Kafka).** Upcoming IPOs in the next 3 months.

### Fully resolved operation
```json
{
  "key": "GET /api/calendar/ipo",
  "method": "GET",
  "path": "/api/calendar/ipo",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "**Requires Advanced+ tier (Advanced, Enterprise, or Enterprise + Kafka).** Upcoming IPOs in the next 3 months.",
    "operationId": "PublicApi.IntelController.ipo_calendar",
    "parameters": [],
    "responses": {
      "200": {
        "content": {
          "application/json": {
            "schema": {
              "properties": {
                "data": {
                  "properties": {
                    "ipos": {
                      "items": {
                        "properties": {
                          "currency": {
                            "nullable": true,
                            "type": "string"
                          },
                          "exchange": {
                            "nullable": true,
                            "type": "string"
                          },
                          "ipo_date": {
                            "format": "date",
                            "nullable": true,
                            "type": "string"
                          },
                          "name": {
                            "nullable": true,
                            "type": "string"
                          },
                          "price_range_high": {
                            "nullable": true,
                            "type": "number"
                          },
                          "price_range_low": {
                            "nullable": true,
                            "type": "number"
                          },
                          "ticker": {
                            "nullable": true,
                            "type": "string"
                          }
                        },
                        "title": "Upcoming IPO",
                        "type": "object"
                      },
                      "type": "array"
                    }
                  },
                  "type": "object"
                }
              },
              "title": "IPO Calendar Response",
              "type": "object"
            }
          }
        },
        "description": "IPO Calendar"
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
    "summary": "IPO Calendar",
    "tags": [
      "intel"
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

## GET /api/companies/listings

Active or Delisted Securities

**Requires Advanced+ tier (Advanced, Enterprise, or Enterprise + Kafka).** All US-traded securities, optionally filtered to delisted as of a given date.

### Fully resolved operation
```json
{
  "key": "GET /api/companies/listings",
  "method": "GET",
  "path": "/api/companies/listings",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "**Requires Advanced+ tier (Advanced, Enterprise, or Enterprise + Kafka).** All US-traded securities, optionally filtered to delisted as of a given date.",
    "operationId": "PublicApi.IntelController.listings",
    "parameters": [
      {
        "description": "",
        "in": "query",
        "name": "status",
        "required": false,
        "schema": {
          "default": "active",
          "enum": [
            "active",
            "delisted"
          ],
          "type": "string"
        }
      },
      {
        "description": "Only used when status=delisted. ISO date.",
        "in": "query",
        "name": "date",
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
              "properties": {
                "data": {
                  "properties": {
                    "date": {
                      "nullable": true,
                      "type": "string"
                    },
                    "listings": {
                      "items": {
                        "properties": {
                          "asset_type": {
                            "nullable": true,
                            "type": "string"
                          },
                          "delisting_date": {
                            "format": "date",
                            "nullable": true,
                            "type": "string"
                          },
                          "exchange": {
                            "nullable": true,
                            "type": "string"
                          },
                          "ipo_date": {
                            "format": "date",
                            "nullable": true,
                            "type": "string"
                          },
                          "name": {
                            "nullable": true,
                            "type": "string"
                          },
                          "status": {
                            "nullable": true,
                            "type": "string"
                          },
                          "ticker": {
                            "nullable": true,
                            "type": "string"
                          }
                        },
                        "title": "Listing",
                        "type": "object"
                      },
                      "type": "array"
                    },
                    "status": {
                      "type": "string"
                    }
                  },
                  "type": "object"
                }
              },
              "title": "Listings Response",
              "type": "object"
            }
          }
        },
        "description": "Listings"
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
    "summary": "Active or Delisted Securities",
    "tags": [
      "intel"
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

## GET /api/market/movers

Top Movers

**Requires Advanced+ tier (Advanced, Enterprise, or Enterprise + Kafka).** Top gainers, top losers, and most actively traded US tickers for the latest session.

### Fully resolved operation
```json
{
  "key": "GET /api/market/movers",
  "method": "GET",
  "path": "/api/market/movers",
  "transport": "http-rest",
  "operation": {
    "callbacks": {},
    "description": "**Requires Advanced+ tier (Advanced, Enterprise, or Enterprise + Kafka).** Top gainers, top losers, and most actively traded US tickers for the latest session.",
    "operationId": "PublicApi.IntelController.movers",
    "parameters": [],
    "responses": {
      "200": {
        "content": {
          "application/json": {
            "schema": {
              "properties": {
                "data": {
                  "properties": {
                    "last_updated": {
                      "nullable": true,
                      "type": "string"
                    },
                    "most_active": {
                      "items": {
                        "properties": {
                          "change": {
                            "nullable": true,
                            "type": "number"
                          },
                          "change_percent": {
                            "nullable": true,
                            "type": "number"
                          },
                          "price": {
                            "nullable": true,
                            "type": "number"
                          },
                          "ticker": {
                            "type": "string"
                          },
                          "volume": {
                            "nullable": true,
                            "type": "number"
                          }
                        },
                        "title": "Mover",
                        "type": "object"
                      },
                      "type": "array"
                    },
                    "top_gainers": {
                      "items": {
                        "properties": {
                          "change": {
                            "nullable": true,
                            "type": "number"
                          },
                          "change_percent": {
                            "nullable": true,
                            "type": "number"
                          },
                          "price": {
                            "nullable": true,
                            "type": "number"
                          },
                          "ticker": {
                            "type": "string"
                          },
                          "volume": {
                            "nullable": true,
                            "type": "number"
                          }
                        },
                        "title": "Mover",
                        "type": "object"
                      },
                      "type": "array"
                    },
                    "top_losers": {
                      "items": {
                        "properties": {
                          "change": {
                            "nullable": true,
                            "type": "number"
                          },
                          "change_percent": {
                            "nullable": true,
                            "type": "number"
                          },
                          "price": {
                            "nullable": true,
                            "type": "number"
                          },
                          "ticker": {
                            "type": "string"
                          },
                          "volume": {
                            "nullable": true,
                            "type": "number"
                          }
                        },
                        "title": "Mover",
                        "type": "object"
                      },
                      "type": "array"
                    }
                  },
                  "type": "object"
                }
              },
              "title": "Movers Response",
              "type": "object"
            }
          }
        },
        "description": "Movers"
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
    "summary": "Top Movers",
    "tags": [
      "intel"
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
