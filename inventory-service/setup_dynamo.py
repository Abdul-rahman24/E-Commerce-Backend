import boto3

def create_inventory_table():
    dynamodb = boto3.client('dynamodb')
    print("Creating 'Inventory' table in AWS...")
    response = dynamodb.create_table(
        TableName='Inventory',
        KeySchema=[{'AttributeName': 'productId', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'productId', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )
    print("Table created successfully!")

if __name__ == "__main__":
    create_inventory_table()