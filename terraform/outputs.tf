output "product_api_endpoint" {
  value = aws_apigatewayv2_api.product_api.api_endpoint
}

output "inventory_api_endpoint" {
  value = aws_apigatewayv2_api.inventory_api.api_endpoint
}