# 🛒 E-Commerce Microservices Platform

A production-ready, cloud-native e-commerce backend built on two complementary paradigms: **synchronous REST microservices** (FastAPI + AWS DynamoDB) for real-time client interactions, and **asynchronous event-driven serverless functions** (AWS Lambda) for high-throughput background processing. Each service is independently deployable and follows clean architecture principles.

---

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
  - [Synchronous REST Layer](#synchronous-rest-layer)
  - [Asynchronous Event-Driven Layer](#asynchronous-event-driven-layer)
  - [End-to-End Flow](#end-to-end-flow)
- [Services Summary](#services-summary)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Data Models](#data-models)
- [API Reference — REST Services](#api-reference--rest-services)
  - [Product Service](#1-product-service--port-8000)
  - [Inventory Service](#2-inventory-service--port-8001)
  - [Cart Service](#3-cart-service--port-8002)
  - [Payment Service](#4-payment-service--port-8003)
  - [Order Service](#5-order-service--port-8004)
  - [Search Service](#6-search-service--port-8005)
- [Event-Driven Services](#event-driven-services)
  - [S3 Bulk Product Ingestion Pipeline](#s3-bulk-product-ingestion-pipeline)
  - [Asynchronous Payment Status Orchestrator](#asynchronous-payment-status-orchestrator)
- [Inter-Service Communication](#inter-service-communication)
- [DynamoDB Schema](#dynamodb-schema)
- [Error Handling](#error-handling)
- [Getting Started](#getting-started)
- [Running the Services](#running-the-services)
- [Design Patterns](#design-patterns)
- [Future Improvements](#future-improvements)

---

## Architecture Overview

### Synchronous REST Layer

The REST layer handles all real-time, user-facing interactions. Each domain is encapsulated in its own independently runnable FastAPI service, communicating over HTTP, with each service owning its own DynamoDB table.

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT / FRONTEND                          │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ HTTP Requests
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌────────────────┐    ┌────────────────────┐   ┌─────────────────┐
│ Product Service│    │   Search Service   │   │  Cart Service   │
│   :8000        │    │      :8005         │   │    :8002        │
└───────┬────────┘    └────────────────────┘   └────────┬────────┘
        │                       ▲                       │
        │ (initialize stock)    │ (index product)       │ (check stock)
        │                       │                       │
        ▼                       │                       ▼
┌────────────────────────────────────────────────────────────────────┐
│                       Inventory Service :8001                      │
└────────────────────────────────────────────────────────────────────┘
        ▲                                               ▲
        │ (reserve / deduct / release)                  │
        │                                               │
┌───────┴────────┐                           ┌──────────┴──────────┐
│  Order Service │                           │   Payment Service   │
│    :8004       │                           │       :8003         │
└───────┬────────┘                           └─────────────────────┘
        │ (fetch cart, clear cart)
        ▼
┌───────────────┐
│  Cart Service │
│    :8002      │
└───────────────┘
```

### Asynchronous Event-Driven Layer

The event-driven layer handles background operations that do not need to block the user. These are serverless AWS Lambda functions triggered directly by infrastructure events, not by HTTP clients.

```
[ Store Admin ]
      │
      │ 1. Uploads new_catalog_2026.csv
      ▼
[ Amazon S3 Bucket ]
      │
      │ ObjectCreated:Put Event (native AWS trigger)
      ▼
[ BulkProductImportLambda ]
      │
      ├──► Parse & validate CSV rows
      ├──► Batch write to Products DynamoDB Table (25 items/batch)
      ├──► Initialize stock to 0 in Inventory Service
      └──► Index each product in Search Service


[ Payment Gateway / Checkout UI ]
      │
      │ 2. Payment completed by customer
      ▼
[ Amazon SNS / EventBridge ]
      │
      │ PaymentSuccessEvent (async notification)
      ▼
[ PaymentSuccessLambda ]
      │
      ├──► Parse order_id & transaction_id from event payload
      ├──► Verify order is in PENDING_PAYMENT state
      ├──► Atomic conditional update: status → PAID
      └──► Idempotency guard (no double-processing on retries)
```

### End-to-End Flow

```
Admin   → S3 Upload            → Bulk import products (async, Lambda)
User    → Search Service       → Find products by keyword
User    → Cart Service         → Add items (validates stock via Inventory Service)
User    → Order Service        → Checkout (fetches Cart, reserves stock via Inventory)
User    → Payment Service      → Initiate payment, receive client_secret
User    → Payment Gateway      → Complete payment on frontend
Gateway → SNS / EventBridge    → Fires PaymentSuccessEvent (async)
Lambda  → Order DynamoDB Table → Updates order status to PAID (Lambda)
Admin   → Order Service        → Update status to SHIPPED/COMPLETED → Inventory deducted
```

---

## Services Summary

### REST Services

| Service | Port | Responsibility | DynamoDB Table |
|---|---|---|---|
| **Product Service** | 8000 | Product catalog CRUD; triggers inventory init & search indexing on create | `Products` |
| **Inventory Service** | 8001 | Stock tracking; atomic reserve / deduct / release operations | `Inventory` |
| **Cart Service** | 8002 | User shopping cart with TTL-based 7-day auto-expiry | `Carts` |
| **Payment Service** | 8003 | Payment initiation, verification, and webhook processing | `Payments` |
| **Order Service** | 8004 | Order lifecycle management; orchestrates Cart + Inventory | `Orders` |
| **Search Service** | 8005 | Full-text product search backed by a DynamoDB scan index | `SearchIndex` |

### Event-Driven Serverless Services

| Lambda Function | Trigger | Responsibility | DynamoDB Table |
|---|---|---|---|
| **BulkProductImportLambda** | S3 `ObjectCreated:Put` | Parse CSV, batch-write products, initialize inventory & search | `Products` |
| **PaymentSuccessLambda** | SNS / EventBridge event | Atomic order status update to `PAID`; idempotency-safe | `Orders` |

---

## Technology Stack

### REST Layer

| Layer | Technology |
|---|---|
| **Framework** | FastAPI (Python) |
| **ASGI Server** | Uvicorn |
| **Database** | AWS DynamoDB (on-demand billing) |
| **AWS SDK** | Boto3 |
| **Validation** | Pydantic v2 |
| **Logging** | Python `logging` module (structured) |
| **HTTP Client** | `requests` (inter-service calls) |

### Event-Driven Layer

| Layer | Technology |
|---|---|
| **Compute** | AWS Lambda (Python runtime) |
| **File Storage / Trigger** | Amazon S3 |
| **Messaging / Trigger** | Amazon SNS or Amazon EventBridge |
| **Failure Handling** | AWS Dead-Letter Queue (SQS DLQ) |
| **Database** | AWS DynamoDB (shared tables with REST layer) |
| **AWS SDK** | Boto3 |

---

## Project Structure

Each REST microservice follows an identical clean architecture layout. The Lambda functions are standalone Python handlers.

```
E-Commerce/
├── product-service/
│   ├── setup_dynamo.py              # One-time DynamoDB table provisioning script
│   └── src/
│       ├── main.py                  # FastAPI app, router registration, exception handlers
│       ├── controllers/
│       │   └── product_controller.py  # Route definitions, HTTP layer
│       ├── services/
│       │   └── product_service.py     # Business logic, inter-service calls
│       ├── repositories/
│       │   └── product_repository.py  # DynamoDB data access layer
│       ├── models/
│       │   └── product.py             # Domain entity (Python dataclass)
│       ├── dto/
│       │   └── product_dto.py         # Pydantic request/response schemas
│       ├── exceptions/
│       │   └── app_exceptions.py      # Custom exception hierarchy
│       └── utils/
│           └── logger.py              # Centralized logger factory
│
├── inventory-service/     # (same structure, port 8001)
├── cart-service/          # (same structure, port 8002)
├── payment-service/       # (same structure, port 8003)
├── order-service/         # (same structure, port 8004)
├── search-service/        # (same structure, port 8005)
│
└── lambdas/
    ├── bulk_product_import/
    │   └── handler.py               # S3-triggered bulk CSV importer
    └── payment_success/
        └── handler.py               # SNS/EventBridge payment status updater
```

### Layer Responsibilities (REST Services)

| Layer | File | Role |
|---|---|---|
| **Controller** | `*_controller.py` | HTTP routing, status codes, request/response binding |
| **Service** | `*_service.py` | Business logic, inter-service orchestration |
| **Repository** | `*_repository.py` | All DynamoDB read/write operations |
| **Model** | `*.py` in `models/` | Pure Python domain entity (dataclass) |
| **DTO** | `*_dto.py` | Pydantic schemas for API validation and serialization |
| **Exception** | `app_exceptions.py` | Typed exceptions (`NotFoundError`, `ConflictError`, etc.) |

---

## Data Models

### Product
```python
product_id: str          # UUID
sku: str                 # Unique product SKU
name: str
description: str
category: str
brand: str
price: float
currency: str            # Default: "USD"
status: str              # "DRAFT" | "ACTIVE" | "INACTIVE"
images: List[str]        # List of image URLs
attributes: Dict[str, Any]  # Flexible key-value product specs
is_deleted: bool         # Soft delete flag
created_at: datetime
updated_at: datetime
```

### Inventory
```python
product_id: str
available_quantity: int   # Stock available for purchase
reserved_quantity: int    # Held for pending orders
updated_at: datetime
```

### Cart / CartItem
```python
# Cart
user_id: str
items: Dict[product_id, CartItem]
expires_at: int          # Unix timestamp; DynamoDB TTL (7 days)
updated_at: datetime

# CartItem
product_id: str
name: str
price: float
quantity: int
```

### Order / OrderItem
```python
# Order
order_id: str            # Format: "ord_<10 hex chars>"
user_id: str
items: List[OrderItem]
total_amount: float
currency: str
status: str              # PENDING_PAYMENT | PAID | CANCELLED | SHIPPED | COMPLETED
created_at: datetime
updated_at: datetime

# OrderItem
product_id: str
name: str
price: float
quantity: int
```

### Payment
```python
payment_id: str          # Format: "pay_<12 hex chars>"
order_id: str
user_id: str
amount: float
currency: str
status: str              # PENDING | SUCCESS | FAILED | REFUNDED
provider: str            # STRIPE | PAYPAL
provider_transaction_id: Optional[str]
created_at: datetime
updated_at: datetime
```

### SearchItem
```python
product_id: str
name: str
description: str
category: str
price: float
images: List[str]
search_tags: str         # Lowercase concatenation of name + description + category
```

---

## API Reference — REST Services

All services return responses in a consistent envelope:

```json
// Success
{ "success": true, "data": { ... } }

// Error
{ "success": false, "error": "Human-readable error message" }
```

---

### 1. Product Service — Port 8000

Base URL: `http://localhost:8000/api/v1/products`

| Method | Endpoint | Description | Request Body |
|---|---|---|---|
| `POST` | `/` | Create a new product | `CreateProductDTO` |
| `GET` | `/` | List all products | — |
| `GET` | `/{product_id}` | Get a product by ID | — |
| `PATCH` | `/{product_id}` | Update product fields | `UpdateProductDTO` |
| `DELETE` | `/{product_id}` | Soft-delete a product | — |

#### `POST /` — Create Product

**Request Body:**
```json
{
  "sku": "LAPTOP-001",
  "name": "Pro Laptop 15",
  "description": "High-performance laptop for professionals",
  "category": "Electronics",
  "brand": "TechBrand",
  "price": 1299.99,
  "currency": "USD",
  "images": ["https://cdn.example.com/img1.jpg"],
  "attributes": {
    "ram": "16GB",
    "storage": "512GB SSD"
  }
}
```

**Response `201 Created`:**
```json
{
  "success": true,
  "data": {
    "product_id": "3f8a2c1d-...",
    "sku": "LAPTOP-001",
    "name": "Pro Laptop 15",
    "status": "DRAFT",
    "price": 1299.99,
    "currency": "USD",
    "created_at": "2026-06-24T10:00:00Z",
    "updated_at": "2026-06-24T10:00:00Z"
  }
}
```

> **Side Effects on Create:** Automatically triggers `POST /api/v1/inventory/initialize` on the Inventory Service and `POST /api/v1/search/index` on the Search Service. Both calls are fire-and-forget — a failure does not roll back product creation.

#### `PATCH /{product_id}` — Update Product

**Request Body** (all fields optional):
```json
{
  "name": "Updated Name",
  "description": "New description",
  "price": 999.99,
  "status": "ACTIVE"
}
```

---

### 2. Inventory Service — Port 8001

Base URL: `http://localhost:8001/api/v1/inventory`

| Method | Endpoint | Description | Request Body |
|---|---|---|---|
| `GET` | `/{product_id}` | Get stock levels for a product | — |
| `POST` | `/initialize` | Initialize stock at 0 (called by Product Service) | `InitializeInventoryDTO` |
| `POST` | `/restock` | Add available stock (verifies product exists first) | `InventoryTransactionDTO` |
| `POST` | `/reserve` | Move quantity from available → reserved | `InventoryTransactionDTO` |
| `POST` | `/release` | Move quantity from reserved → available (on cancel) | `InventoryTransactionDTO` |
| `POST` | `/deduct` | Permanently remove reserved stock (on ship/complete) | `InventoryTransactionDTO` |

#### `GET /{product_id}` — Get Inventory

**Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "product_id": "3f8a2c1d-...",
    "available_quantity": 45,
    "reserved_quantity": 5,
    "updated_at": "2026-06-24T11:00:00Z"
  }
}
```

#### `POST /reserve` — Reserve Stock

**Request Body:**
```json
{
  "product_id": "3f8a2c1d-...",
  "quantity": 2
}
```

> All quantity mutations (`reserve`, `release`, `deduct`, `restock`) use a **DynamoDB atomic conditional update** with `ConditionExpression` to prevent negative stock. A `ConflictError (409)` is raised if the condition fails.

---

### 3. Cart Service — Port 8002

Base URL: `http://localhost:8002/api/v1/cart`

> **Authentication:** All endpoints require the `X-User-Id` header to identify the user.

| Method | Endpoint | Description | Request Body | Header |
|---|---|---|---|---|
| `GET` | `/` | Get the current user's cart | — | `X-User-Id` |
| `POST` | `/items` | Add an item to the cart | `AddCartItemDTO` | `X-User-Id` |
| `PATCH` | `/items/{product_id}` | Update quantity of a cart item | `UpdateCartItemDTO` | `X-User-Id` |
| `DELETE` | `/items/{product_id}` | Remove a specific item from cart | — | `X-User-Id` |
| `DELETE` | `/` | Clear entire cart | — | `X-User-Id` |

#### `POST /items` — Add Item

**Request Body:**
```json
{
  "product_id": "3f8a2c1d-...",
  "quantity": 2
}
```

**Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "user_id": "user_123",
    "items": [
      {
        "product_id": "3f8a2c1d-...",
        "name": "Pro Laptop 15",
        "price": 1299.99,
        "quantity": 2,
        "item_total": 2599.98
      }
    ],
    "cart_total": 2599.98,
    "updated_at": "2026-06-24T11:30:00Z"
  }
}
```

> **Validation on Add:** Checks Inventory Service for available stock before adding. If requested quantity exceeds available stock, returns `400 Bad Request`. Product name and price are fetched live from Product Service and snapshotted into the cart.

> **Cart TTL:** Cart items automatically expire after **7 days** via DynamoDB TTL on the `expiresAt` attribute.

#### `PATCH /items/{product_id}` — Update Item Quantity

**Request Body:**
```json
{ "quantity": 3 }
```

> Setting `quantity` to `0` is equivalent to removing the item.

---

### 4. Payment Service — Port 8003

Base URL: `http://localhost:8003/api/v1/payments`

> **Authentication:** `POST /initiate` requires `X-User-Id` header.

| Method | Endpoint | Description | Request Body |
|---|---|---|---|
| `POST` | `/initiate` | Create a payment intent for an order | `InitiatePaymentDTO` |
| `POST` | `/verify` | Confirm payment success with provider transaction ID | `VerifyPaymentDTO` |
| `POST` | `/webhook` | Handle asynchronous callback from payment gateway | `WebhookPayloadDTO` |

#### `POST /initiate` — Initiate Payment

**Request Body:**
```json
{
  "order_id": "ord_a1b2c3d4e5",
  "amount": 2599.98,
  "currency": "USD",
  "provider": "STRIPE"
}
```

**Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "payment_id": "pay_abc123def456",
    "order_id": "ord_a1b2c3d4e5",
    "amount": 2599.98,
    "currency": "USD",
    "status": "PENDING",
    "provider": "STRIPE",
    "client_secret": "secret_<mock_token>",
    "created_at": "2026-06-24T12:00:00Z",
    "updated_at": "2026-06-24T12:00:00Z"
  }
}
```

> **Note:** The `client_secret` is a mock token. In production, this is the actual Stripe `PaymentIntent` client secret passed to the frontend SDK.

#### `POST /verify` — Verify Payment

**Request Body:**
```json
{
  "payment_id": "pay_abc123def456",
  "provider_transaction_id": "pi_stripe_xyz"
}
```

#### `POST /webhook` — Payment Gateway Webhook

**Request Body:**
```json
{
  "event_type": "payment_intent.succeeded",
  "provider_transaction_id": "pi_stripe_xyz",
  "status": "succeeded"
}
```

Supported `event_type` values: `payment_intent.succeeded`, `payment_intent.payment_failed`

---

### 5. Order Service — Port 8004

Base URL: `http://localhost:8004/api/v1/orders`

> **Authentication:** `POST /` requires `X-User-Id` header.

| Method | Endpoint | Description | Request Body |
|---|---|---|---|
| `POST` | `/` | Create order from cart (checkout) | — (reads cart via header) |
| `GET` | `/{order_id}` | Get order by ID | — |
| `GET` | `/user/{user_id}` | Get all orders for a user | — |
| `PATCH` | `/{order_id}/status` | Update order status | `OrderStatusUpdateDTO` |
| `PATCH` | `/{order_id}/cancel` | Cancel an order | — |

#### `POST /` — Create Order (Checkout)

No request body required. The service reads the user's cart automatically via the `X-User-Id` header.

**Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "order_id": "ord_a1b2c3d4e5",
    "user_id": "user_123",
    "items": [
      {
        "product_id": "3f8a2c1d-...",
        "name": "Pro Laptop 15",
        "price": 1299.99,
        "quantity": 2
      }
    ],
    "total_amount": 2599.98,
    "currency": "USD",
    "status": "PENDING_PAYMENT",
    "created_at": "2026-06-24T12:00:00Z",
    "updated_at": "2026-06-24T12:00:00Z"
  }
}
```

> **Checkout Flow:**
> 1. Fetch cart from Cart Service using `X-User-Id`
> 2. Reserve stock for every item via Inventory Service (atomic)
> 3. Persist the Order record with status `PENDING_PAYMENT`
> 4. Clear the user's cart
>
> If stock reservation fails for any item, a `409 Conflict` is returned.

#### `PATCH /{order_id}/status` — Update Status

**Request Body:**
```json
{ "status": "SHIPPED" }
```

Valid statuses: `PENDING_PAYMENT`, `PAID`, `CANCELLED`, `SHIPPED`, `COMPLETED`

> **Inventory side effect:** When status changes to `SHIPPED` or `COMPLETED`, the service calls `POST /deduct` on the Inventory Service to permanently remove the reserved quantity.

#### `PATCH /{order_id}/cancel` — Cancel Order

No request body required.

> Orders with status `SHIPPED` or `COMPLETED` cannot be cancelled (`400 Bad Request`). On successful cancellation, the Inventory Service's `/release` endpoint is called to restore reserved stock to available.

---

### 6. Search Service — Port 8005

Base URL: `http://localhost:8005/api/v1/search`

| Method | Endpoint | Description | Params / Body |
|---|---|---|---|
| `GET` | `/` | Search products by keyword | `?q=<query>` (query param) |
| `POST` | `/index` | Index a product (internal, called by Product Service) | `IndexProductDTO` |

#### `GET /?q=laptop` — Search Products

**Response `200 OK`:**
```json
{
  "success": true,
  "data": [
    {
      "product_id": "3f8a2c1d-...",
      "name": "Pro Laptop 15",
      "category": "Electronics",
      "price": 1299.99,
      "image_url": "https://cdn.example.com/img1.jpg"
    }
  ]
}
```

**Response `404 Not Found`** (no results):
```json
{ "success": false, "error": " Products Unavailable " }
```

> **Search Implementation:** The `searchTags` field stores a lowercase concatenation of `name + description + category`. Queries are matched using a DynamoDB `Scan` with `FilterExpression contains`. Suitable for development and small catalogs; production systems should replace this with OpenSearch or Elasticsearch.

#### `POST /index` — Index Product (Internal)

This endpoint is called automatically by the Product Service on product creation and by `BulkProductImportLambda` after a batch CSV import. It is not intended to be called directly by end-users.

**Request Body:**
```json
{
  "product_id": "3f8a2c1d-...",
  "name": "Pro Laptop 15",
  "description": "High-performance laptop",
  "category": "Electronics",
  "price": 1299.99,
  "images": ["https://cdn.example.com/img1.jpg"]
}
```

---

## Event-Driven Services

These two serverless Lambda functions extend the platform with background processing capabilities. They are **not HTTP servers** — they are deployed to AWS Lambda and triggered automatically by native AWS infrastructure events, operating entirely independently of the REST layer.

---

### S3 Bulk Product Ingestion Pipeline

#### What It Does

Allows store administrators to catalog thousands of products simultaneously by uploading a single `.csv` file to an S3 bucket — instead of making individual `POST /products` HTTP calls. AWS infrastructure detects the file and processes the entire catalog in the background without blocking any user-facing APIs.

#### Trigger

An `ObjectCreated:Put` event fires automatically when a `.csv` file is uploaded to the designated S3 bucket path (e.g., `s3://our-ecommerce-uploads/products/`).

#### Technical Workflow

```
1. Admin uploads new_catalog_2026.csv to S3
        │
        ▼ S3 ObjectCreated:Put event
2. BulkProductImportLambda is invoked
   Payload contains: { bucket_name, file_key }
        │
        ▼ boto3: s3.get_object()
3. CSV is streamed directly into memory (no disk I/O)
   csv.DictReader parses rows
        │
        ▼ Validates required columns: sku, name, price, category
4. UUID and timestamps are generated per row
        │
        ▼ DynamoDB batch_writer() — max 25 items per batch
5. Products written to Products table in chunks
        │
        ├──► Inventory Service: POST /initialize (stock = 0)
        └──► Search Service:    POST /index (product indexed)
```

#### Lambda Handler (Pattern)

```python
import csv
import uuid
import codecs
import boto3
from datetime import datetime, timezone

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Products')

def lambda_handler(event, context):
    # 1. Extract Bucket and Key from S3 event
    record = event['Records'][0]
    bucket_name = record['s3']['bucket']['name']
    file_key = record['s3']['object']['key']

    # 2. Stream and decode CSV directly from S3
    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    csv_reader = csv.DictReader(codecs.getreader('utf-8')(response['Body']))

    # 3. Batch write to DynamoDB (25 items per batch = max DynamoDB allows)
    with table.batch_writer() as batch:
        for row in csv_reader:
            product_item = {
                'product_id': str(uuid.uuid4()),
                'sku': row['sku'],
                'name': row['name'],
                'price': float(row['price']),
                'status': 'ACTIVE',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            batch.put_item(Item=product_item)

    return {"status": "Success", "message": f"Processed {file_key}"}
```

#### Required CSV Format

| Column | Type | Required | Notes |
|---|---|---|---|
| `sku` | string | ✅ | Must be unique |
| `name` | string | ✅ | Product display name |
| `price` | float | ✅ | Must be a valid number |
| `category` | string | ✅ | Used for search tagging |
| `description` | string | ⬜ | Optional; used in search index |
| `brand` | string | ⬜ | Optional |

#### Engineering Highlights

**DynamoDB Batch Writer** — Bundles writes into groups of 25 (the AWS maximum per batch call). This significantly reduces network round-trips and lowers consumed Write Request Units (WRUs) compared to individual `put_item` calls for each row.

**Memory-Efficient Streaming** — `s3.get_object()` streams the file body rather than downloading it to Lambda's ephemeral `/tmp` disk. This allows processing of very large CSVs (tens of thousands of rows) within Lambda's memory constraints.

**Scalability** — AWS Lambda automatically provisions additional concurrent instances if multiple admins upload CSVs simultaneously, ensuring zero interference with the live storefront APIs.

**Dead-Letter Queue** — The Lambda is configured with an AWS SQS DLQ. If a CSV is malformed or a transient database error occurs, the failed event is captured for safe developer inspection and replay without data loss.

---

### Asynchronous Payment Status Orchestrator

#### What It Does

Bridges the gap between external payment gateways (Stripe, Razorpay, PayPal) and the internal Orders database. When a customer completes payment on the checkout frontend, this service atomically updates the corresponding order status from `PENDING_PAYMENT` to `PAID`, immediately unlocking the order for warehouse fulfillment.

#### Trigger

A `PaymentSuccessEvent` message published to **Amazon SNS** or **Amazon EventBridge** by the payment gateway (or by the Payment Service webhook handler). The event broker routes it to this Lambda function asynchronously.

#### Technical Workflow

```
1. Customer completes payment on checkout UI
        │
        ▼ Payment Gateway fires webhook / SNS message
2. PaymentSuccessLambda is invoked
   Payload contains: { order_id, transaction_id, amount_paid, payment_method }
        │
        ▼ boto3: Orders DynamoDB Table lookup by order_id
3. Verify: order exists AND status == PENDING_PAYMENT
        │
        ▼ DynamoDB update_item with ConditionExpression
4. Atomic update:
   - status        → PAID
   - transaction_id → <gateway tx id>
   - updated_at    → now (UTC)
        │
        ├── Success → return { status: "SUCCESS", order: <updated attributes> }
        └── ConditionalCheckFailedException
            → Order already PAID or doesn't exist
            → return { status: "IGNORED" }  ← idempotency guard
```

#### Lambda Handler (Pattern)

```python
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
order_table = dynamodb.Table('Orders')

def lambda_handler(event, context):
    # 1. Parse event payload (EventBridge structure)
    payload = event['detail']
    order_id = payload['order_id']
    transaction_id = payload['transaction_id']

    try:
        # 2. Atomic conditional update — only transitions PENDING_PAYMENT → PAID
        response = order_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression="SET #stat = :paid, transaction_id = :tx, updated_at = :now",
            ConditionExpression="attribute_exists(order_id) AND #stat = :pending",
            ExpressionAttributeNames={
                '#stat': 'status'   # 'status' is a reserved keyword in DynamoDB
            },
            ExpressionAttributeValues={
                ':paid':    'PAID',
                ':tx':      transaction_id,
                ':now':     datetime.now(timezone.utc).isoformat(),
                ':pending': 'PENDING_PAYMENT'
            },
            ReturnValues="ALL_NEW"
        )
        return {"status": "SUCCESS", "order": response['Attributes']}

    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        # Order is already PAID or does not exist — safe to ignore
        return {"status": "IGNORED", "message": "Idempotent check failed or order invalid."}
```

#### Engineering Highlights

**Atomic Conditional Update** — Instead of a read-modify-write cycle (fetch order → update in Python → write back), the Lambda uses a single DynamoDB `update_item` with `ConditionExpression`. This is atomic at the database level, meaning no race condition can occur even if two Lambda instances process events concurrently.

**Idempotency** — Payment gateways may fire the same success event more than once due to network retries. The `ConditionExpression` (`status = :pending`) ensures the database is only mutated once. Any subsequent duplicate events return `IGNORED` without touching the database.

**Reserved Keyword Handling** — `status` is a DynamoDB reserved word. The handler uses `ExpressionAttributeNames` (`#stat`) to safely alias it, preventing runtime expression parse errors.

**Dead-Letter Queue** — Failed Lambda invocations (e.g., due to a transient DynamoDB outage) are automatically captured in an SQS DLQ for safe developer replay, ensuring no payment event is silently dropped.

---

## Inter-Service Communication

All REST inter-service calls are synchronous HTTP using the `requests` library with a 5-second timeout. Lambda functions write directly to DynamoDB via Boto3.

### REST ↔ REST Calls

| Caller | Called Service | Trigger | Endpoint |
|---|---|---|---|
| Product Service | Inventory Service | Product created | `POST /api/v1/inventory/initialize` |
| Product Service | Search Service | Product created | `POST /api/v1/search/index` |
| Inventory Service | Product Service | Before restock | `GET /api/v1/products/{id}` (existence check) |
| Cart Service | Inventory Service | Add item to cart | `GET /api/v1/inventory/{id}` (stock check) |
| Cart Service | Product Service | Add item to cart | `GET /api/v1/products/{id}` (fetch name & price) |
| Order Service | Cart Service | Checkout | `GET /api/v1/cart/` |
| Order Service | Inventory Service | Checkout | `POST /api/v1/inventory/reserve` |
| Order Service | Inventory Service | Ship / Complete | `POST /api/v1/inventory/deduct` |
| Order Service | Inventory Service | Cancel | `POST /api/v1/inventory/release` |
| Order Service | Cart Service | After order creation | `DELETE /api/v1/cart/` |

### Lambda → DynamoDB / REST Calls

| Lambda | Action | Target |
|---|---|---|
| `BulkProductImportLambda` | Batch write products | `Products` DynamoDB Table |
| `BulkProductImportLambda` | Initialize stock to 0 | Inventory Service `POST /initialize` |
| `BulkProductImportLambda` | Index new products | Search Service `POST /index` |
| `PaymentSuccessLambda` | Atomic status update | `Orders` DynamoDB Table |

### Resilience Strategy

- Product creation does **not** fail if Inventory or Search services are unavailable (fire-and-forget).
- Cart operations fail gracefully if Inventory is unreachable (logs a warning and proceeds).
- Order creation fails explicitly if Cart or Inventory are unreachable (`DatabaseError → 500`).
- Lambda functions are backed by **SQS Dead-Letter Queues** — failed events are never silently dropped.
- `PaymentSuccessLambda` is idempotent — duplicate events from the payment gateway are safely no-ops.

---

## DynamoDB Schema

### `Products` Table

| Attribute | Type | Key |
|---|---|---|
| `productId` | String | **Partition Key (PK)** |
| `sku` | String | — |
| `name` | String | — |
| `price` | Number (Decimal) | — |
| `status` | String | — |
| `is_deleted` | Boolean | — (soft delete flag) |
| `created_at` | String (ISO 8601) | — |
| `updated_at` | String (ISO 8601) | — |

### `Inventory` Table

| Attribute | Type | Key |
|---|---|---|
| `productId` | String | **Partition Key (PK)** |
| `availableQuantity` | Number | — |
| `reservedQuantity` | Number | — |
| `updated_at` | String (ISO 8601) | — |

### `Carts` Table

| Attribute | Type | Key |
|---|---|---|
| `userId` | String | **Partition Key (PK)** |
| `items` | Map | — (nested product map) |
| `updatedAt` | String (ISO 8601) | — |
| `expiresAt` | Number | — (**TTL attribute**, 7-day expiry) |

### `Orders` Table

| Attribute | Type | Key |
|---|---|---|
| `orderId` | String | **Partition Key (PK)** |
| `userId` | String | **GSI: `UserIdIndex` (PK)** |
| `items` | List | — |
| `totalAmount` | Number (Decimal) | — |
| `status` | String | — (mutated atomically by `PaymentSuccessLambda`) |
| `transaction_id` | String | — (written by `PaymentSuccessLambda`) |
| `createdAt` | String (ISO 8601) | — |
| `updatedAt` | String (ISO 8601) | — |

### `Payments` Table

| Attribute | Type | Key |
|---|---|---|
| `paymentId` | String | **Partition Key (PK)** |
| `orderId` | String | **GSI: `OrderIdIndex` (PK)** |
| `status` | String | — |
| `provider` | String | — |
| `providerTxId` | String | — |
| `amount` | Number (Decimal) | — |

### `SearchIndex` Table

| Attribute | Type | Key |
|---|---|---|
| `productId` | String | **Partition Key (PK)** |
| `name` | String | — |
| `category` | String | — |
| `price` | Number (Decimal) | — |
| `searchTags` | String | — (lowercase full-text field for `contains` scan) |

---

## Error Handling

### REST Services

Each service uses a custom exception hierarchy that maps to standard HTTP status codes:

```python
AppError (base)
├── NotFoundError       → 404 Not Found
├── BadRequestError     → 400 Bad Request
├── ConflictError       → 409 Conflict
└── DatabaseError       → 500 Internal Server Error
```

All exceptions are caught by a global FastAPI `exception_handler` and returned in the standard error envelope:

```json
{ "success": false, "error": "Descriptive error message" }
```

Pydantic `RequestValidationError` is also caught globally and returns `422 Unprocessable Entity`.

### Lambda Functions

| Scenario | Handling |
|---|---|
| Malformed CSV / missing columns | Row is skipped; logged to CloudWatch |
| DynamoDB transient error | Lambda retries automatically; after max retries, event goes to SQS DLQ |
| Duplicate payment event | `ConditionalCheckFailedException` caught; returns `IGNORED` (idempotent no-op) |
| Order not found in Orders table | `ConditionalCheckFailedException` caught; returns `IGNORED` |

---

## Getting Started

### Prerequisites

- Python 3.10+
- AWS account with DynamoDB, S3, Lambda, SNS/EventBridge access
- AWS CLI configured (`aws configure`)
- `pip` package manager

### Installation

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd E-Commerce
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install fastapi uvicorn boto3 requests pydantic
   ```

4. Configure AWS credentials:
   ```bash
   aws configure
   # Enter your AWS Access Key, Secret Key, and region (e.g., ap-south-1)
   ```

### Provision DynamoDB Tables

Run the `setup_dynamo.py` script for each service. These are one-time setup scripts:

```bash
python product-service/setup_dynamo.py
python inventory-service/setup_dynamo.py
python cart-service/setup_dynamo.py       # Also enables TTL on Carts table
python order-service/setup_dynamo.py      # Creates Orders table with UserIdIndex GSI
python payment-service/setup_dynamo.py    # Creates Payments table with OrderIdIndex GSI
python search-service/setup_dynamo.py
```

### Deploy Lambda Functions

1. Package each Lambda handler and its dependencies into a `.zip` file.
2. Upload to AWS Lambda via the AWS Console or AWS CLI:
   ```bash
   zip bulk_import.zip lambdas/bulk_product_import/handler.py
   aws lambda update-function-code \
     --function-name BulkProductImportLambda \
     --zip-file fileb://bulk_import.zip
   ```
3. Configure triggers in AWS Console:
   - **BulkProductImportLambda** → S3 bucket → Event type: `ObjectCreated:Put`
   - **PaymentSuccessLambda** → SNS Topic or EventBridge Rule → Event pattern: payment success
4. Attach an SQS Dead-Letter Queue to each Lambda under **Configuration → Asynchronous invocation**.

---

## Running the Services

Each REST service must be started separately. Open a separate terminal for each:

```bash
# Terminal 1 — Product Service (port 8000)
cd product-service/src && python main.py

# Terminal 2 — Inventory Service (port 8001)
cd inventory-service/src && python main.py

# Terminal 3 — Cart Service (port 8002)
cd cart-service/src && python main.py

# Terminal 4 — Payment Service (port 8003)
cd payment-service/src && python main.py

# Terminal 5 — Order Service (port 8004)
cd order-service/src && python main.py

# Terminal 6 — Search Service (port 8005)
cd search-service/src && python main.py
```

> **Lambda functions** do not need to be started manually — they run on AWS and are triggered automatically by S3 / SNS / EventBridge events.

### Interactive API Docs

Once a service is running, visit its auto-generated Swagger UI:

| Service | Swagger URL |
|---|---|
| Product | http://localhost:8000/docs |
| Inventory | http://localhost:8001/docs |
| Cart | http://localhost:8002/docs |
| Payment | http://localhost:8003/docs |
| Order | http://localhost:8004/docs |
| Search | http://localhost:8005/docs |

---

## Design Patterns

### Clean / Layered Architecture
Each REST service is structured as `Controller → Service → Repository → DynamoDB`. Business logic lives exclusively in the service layer; the controller only handles HTTP concerns; the repository only handles database I/O.

### Repository Pattern
All DynamoDB interactions are abstracted behind repository classes (`DynamoDB*Repository`). Domain models (dataclasses) are decoupled from the storage format via `_to_item()` and `_to_entity()` mapper methods.

### DTO Pattern
Pydantic models separate the external API contract (`*DTO`) from internal domain entities (`*` dataclasses), providing automatic validation, serialization, and OpenAPI schema generation.

### Soft Delete
Products are never physically removed from DynamoDB. An `is_deleted` flag is set to `True`, and all read queries filter out deleted records at the repository layer.

### Atomic Inventory Updates
The Inventory Service uses DynamoDB's `UpdateExpression` with `ConditionExpression` to perform **atomic, race-condition-safe** stock operations, preventing overselling without requiring distributed locks.

### TTL-based Cart Expiry
Shopping carts automatically expire after 7 days using DynamoDB's native **Time-To-Live (TTL)** feature, eliminating the need for a scheduled cleanup job.

### Fire-and-Forget Side Effects
When a product is created, inventory initialization and search indexing are best-effort. A downstream service failure does not roll back product creation, keeping the Product Service resilient.

### Saga Pattern (Partial)
The Order Service implements a partial Saga: it reserves inventory for all items before committing the order, and releases inventory on cancellation. Full compensating rollback for mid-checkout partial reservations is a noted future improvement.

### Event-Driven Decoupling
The Bulk Import Lambda and Payment Lambda operate completely outside the HTTP request cycle. They react to native AWS infrastructure events (S3 file uploads, SNS/EventBridge messages), ensuring that heavy background operations never degrade the latency of user-facing REST APIs.

### Idempotent Event Processing
The `PaymentSuccessLambda` uses a DynamoDB `ConditionExpression` to guarantee that a payment event — even if delivered multiple times by the gateway — is processed exactly once. This is a standard pattern for safe event-driven systems.

### Cost-Optimized Batch Writes
The `BulkProductImportLambda` uses DynamoDB's `batch_writer()` to bundle writes into groups of 25 (the DynamoDB maximum), reducing network calls and Write Request Unit consumption during large catalog imports.

---

## Future Improvements

- **API Gateway / Reverse Proxy** — Unify all REST services behind a single entry point (AWS API Gateway, Nginx, or Kong) for routing, auth, and rate limiting.
- **Full Event-Driven Migration** — Replace synchronous REST inter-service calls with SNS/SQS messages for better resilience and decoupling across all services.
- **Full-text Search Engine** — Replace the DynamoDB `Scan` in the Search Service with OpenSearch or Elasticsearch for scalable, relevance-ranked results.
- **Authentication & Authorization** — Implement JWT-based auth and replace the `X-User-Id` header with proper token validation middleware.
- **Containerization** — Wrap each REST service in a Docker container and orchestrate with Docker Compose or Kubernetes.
- **Distributed Tracing** — Add correlation IDs and integrate with AWS X-Ray or OpenTelemetry for end-to-end tracing across REST services and Lambda functions.
- **Full Saga Compensation** — Implement rollback logic for partial inventory reservations during a failed checkout.
- **Webhook Security** — Add signature verification (e.g., Stripe webhook HMAC signature) before processing payment events.
- **CSV Validation Layer** — Add a pre-processing step to `BulkProductImportLambda` that validates all rows before writing any to DynamoDB, enabling atomic all-or-nothing batch imports.
- **GSI on `providerTxId`** — Add a Global Secondary Index on the `Payments` table's `providerTxId` column to replace the current full-table `Scan` used in webhook lookups.

---

*Built with FastAPI · AWS Lambda · AWS DynamoDB · Amazon S3 · Amazon SNS / EventBridge · Python 3*