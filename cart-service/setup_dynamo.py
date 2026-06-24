import boto3
import time

def setup_cart_table():
    dynamodb_client = boto3.client('dynamodb')
    table_name = 'Carts'
    
    try:
        print(f"Creating '{table_name}' table...")
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[{'AttributeName': 'userId', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'userId', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        print("Waiting for table to be active...")
        waiter = dynamodb_client.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        print("Enabling Time-To-Live (TTL) on 'expiresAt' attribute...")
        dynamodb_client.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'expiresAt'
            }
        )
        print("Cart table and TTL successfully configured!")
        
    except dynamodb_client.exceptions.ResourceInUseException:
        print(f"Table '{table_name}' already exists.")

if __name__ == "__main__":
    setup_cart_table()