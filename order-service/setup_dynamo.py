import boto3

def setup_order_table():
    dynamodb_client = boto3.client('dynamodb')
    table_name = 'Orders'
    
    try:
        print(f"Creating '{table_name}' table...")
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[{'AttributeName': 'orderId', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'orderId', 'AttributeType': 'S'},
                {'AttributeName': 'userId', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'UserIdIndex',
                    'KeySchema': [{'AttributeName': 'userId', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("Order table successfully configured!")
    except dynamodb_client.exceptions.ResourceInUseException:
        print(f"Table '{table_name}' already exists.")

if __name__ == "__main__":
    setup_order_table()