import boto3

def setup_search_table():
    dynamodb_client = boto3.client('dynamodb')
    table_name = 'SearchIndex'
    
    try:
        print(f"Creating '{table_name}' table...")
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[{'AttributeName': 'productId', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'productId', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        print("Search table successfully configured!")
    except dynamodb_client.exceptions.ResourceInUseException:
        print(f"Table '{table_name}' already exists.")

if __name__ == "__main__":
    setup_search_table()