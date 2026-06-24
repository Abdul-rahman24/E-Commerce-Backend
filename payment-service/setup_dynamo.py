import boto3

def setup_payment_table():
    dynamodb_client = boto3.client('dynamodb')
    table_name = 'Payments'
    
    try:
        print(f"Creating '{table_name}' table...")
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[{'AttributeName': 'paymentId', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'paymentId', 'AttributeType': 'S'},
                {'AttributeName': 'orderId', 'AttributeType': 'S'} # Useful for indexing later
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'OrderIdIndex',
                    'KeySchema': [{'AttributeName': 'orderId', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("Payment table successfully configured!")
    except dynamodb_client.exceptions.ResourceInUseException:
        print(f"Table '{table_name}' already exists.")

if __name__ == "__main__":
    setup_payment_table()