terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-southeast-1"
}

  # This automatically applies these tags to EVERY resource
  default_tags {
    tags = {
      CostCentre         = "YourCostCentreID"
      ApplicationService = "ECommerceBackend"
    }
  }
}

# ==============================================================================
# 1. DYNAMODB TABLES
# ==============================================================================

resource "aws_dynamodb_table" "products" {
  name         = "products_abd"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "productId"

  attribute {
    name = "productId"
    type = "S"
  }
}

resource "aws_dynamodb_table" "inventory" {
  name         = "inventory_abd"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "productId"

  attribute {
    name = "productId"
    type = "S"
  }
}

resource "aws_dynamodb_table" "cart" {
  name         = "cart_abd"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"

  attribute {
    name = "userId"
    type = "S"
  }

  tags = {
    ApplicationService = "CartService"
  }
}

resource "aws_dynamodb_table" "orders" {
  name         = "orders_abd"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "orderId"

  attribute {
    name = "orderId"
    type = "S"
  }

  attribute {
    name = "userId"
    type = "S"
  }

  global_secondary_index {
    name               = "UserIdIndex"
    hash_key           = "userId"
    projection_type    = "ALL"
  }
}

resource "aws_dynamodb_table" "payments" {
  name             = "payments_abd"
  billing_mode     = "PAY_PER_REQUEST"
  hash_key         = "paymentId"
  stream_enabled   = true
  stream_view_type = "NEW_IMAGE"

  attribute {
    name = "paymentId"
    type = "S"
  }

  attribute {
    name = "orderId"
    type = "S"
  }

  global_secondary_index {
    name               = "OrderIdIndex"
    hash_key           = "orderId"
    projection_type    = "ALL"
  }
}

resource "aws_dynamodb_table" "searchindex" {
  name         = "searchindex_abd"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "productId"

  attribute {
    name = "productId"
    type = "S"
  }

  tags = {
    ApplicationService = "SearchService"
  }
}

# ==============================================================================
# 2. S3 BUCKET
# ==============================================================================

resource "aws_s3_bucket" "product_import" {
  bucket = "product-import-eda-abd"
}

# ==============================================================================
# 3. SQS QUEUES
# ==============================================================================

resource "aws_sqs_queue" "cart_cleanup" {
  name = "CartCleanupQueue_abd"
}

resource "aws_sqs_queue" "inventory_queue" {
  name = "InventoryQueue_abd"
}

# ==============================================================================
# 4. SNS TOPIC
# ==============================================================================

resource "aws_sns_topic" "order_events" {
  name = "OrderEventsTopic_abd"
}

# ==============================================================================
# 5. LAMBDA FUNCTIONS
# ==============================================================================

resource "aws_lambda_function" "product_service" {
  function_name = "Product_Service_abd"
  role          = "arn:aws:iam::726101441380:role/AWS_Abdul"
  handler       = "src.main.handler"
  runtime       = "python3.13"
  filename      = "dummy.zip"
  timeout       = 30
  
  environment {
    variables = {
      INVENTORY_SERVICE_URL = "https://owyllwzwo5.execute-api.ap-southeast-1.amazonaws.com/v1/inventory"
      SEARCH_SERVICE_URL    = "https://iy8sclbx9l.execute-api.ap-southeast-1.amazonaws.com/v1/search"
    }
  }
}

resource "aws_lambda_function" "inventory_service" {
  function_name = "Inventory_Service_abd"
  role          = "arn:aws:iam::726101441380:role/AWS_Abdul"
  handler       = "src.main.handler"
  runtime       = "python3.13"
  filename      = "dummy.zip"
  timeout       = 30
  memory_size   = 512
  
  environment {
    variables = {
      PRODUCT_SERVICE_URL = "https://oowum3m5c4.execute-api.ap-southeast-1.amazonaws.com/v1/products"
    }
  }
}

resource "aws_lambda_function" "cart_service" {
  function_name = "Cart_Service_abd"
  role          = "arn:aws:iam::726101441380:role/AWS_Abdul"
  handler       = "src.main.handler"
  runtime       = "python3.13"
  filename      = "dummy.zip"
  timeout       = 30
  
  environment {
    variables = {
      INVENTORY_SERVICE_URL = "https://owyllwzwo5.execute-api.ap-southeast-1.amazonaws.com/v1/inventory"
      PRODUCT_SERVICE_URL   = "https://oowum3m5c4.execute-api.ap-southeast-1.amazonaws.com/v1/products"
    }
  }
}

resource "aws_lambda_function" "payment_service" {
  function_name = "Payment_Service_abd"
  role          = "arn:aws:iam::726101441380:role/AWS_Abdul"
  handler       = "src.main.handler"
  runtime       = "python3.13"
  filename      = "dummy.zip"
  timeout       = 30
}

resource "aws_lambda_function" "order_service" {
  function_name = "Order_Service_abd"
  role          = "arn:aws:iam::726101441380:role/AWS_Abdul"
  handler       = "src.main.handler"
  runtime       = "python3.13"
  filename      = "dummy.zip"
  timeout       = 30
  
  environment {
    variables = {
      CART_SERVICE_URL       = "https://rld8go3jd8.execute-api.ap-southeast-1.amazonaws.com/v1/cart"
      INVENTORY_SERVICE_URL  = "https://owyllwzwo5.execute-api.ap-southeast-1.amazonaws.com/v1/inventory"
      ORDER_EVENTS_TOPIC_ARN = "arn:aws:sns:ap-southeast-1:726101441380:OrderEventsTopic_abd"
      ORDER_TABLE_NAME       = "orders_abd"
    }
  }
}

resource "aws_lambda_function" "search_service" {
  function_name = "Search_Service_abd"
  role          = "arn:aws:iam::726101441380:role/AWS_Abdul"
  handler       = "src.main.handler"
  runtime       = "python3.13"
  filename      = "dummy.zip"
  timeout       = 30
}

resource "aws_lambda_function" "product_import_eda" {
  function_name = "product_import_eda_abd"
  role          = "arn:aws:iam::726101441380:role/AWS_Abdul"
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.13"
  filename      = "dummy.zip"
  timeout       = 30
  memory_size   = 512
}

resource "aws_lambda_function" "order_status_eda" {
  function_name = "order-status-eda-abd"
  role          = "arn:aws:iam::726101441380:role/AWS_Abdul"
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.13"
  filename      = "dummy.zip"
}

resource "aws_lambda_function" "cart_cleanup_func" {
  function_name = "CartCleanupFunction_abd"
  role          = "arn:aws:iam::726101441380:role/AWS_Abdul"
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.13"
  filename      = "dummy.zip"
  
  environment {
    variables = {
      CART_TABLE_NAME = "cart_abd"
    }
  }
}

# ==============================================================================
# 6. API GATEWAYS (HTTP APIs)
# ==============================================================================

resource "aws_apigatewayv2_api" "product_api" {
  name          = "product-api-abd"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_api" "inventory_api" {
  name          = "Inventory-API-abd"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_api" "cart_api" {
  name          = "Cart-API-abd"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_api" "payment_api" {
  name          = "Payment-API-abd"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_api" "order_api" {
  name          = "Order-API-abd"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_api" "search_api" {
  name          = "Search-API-abd"
  protocol_type = "HTTP"
}