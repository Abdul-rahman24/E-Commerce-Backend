from fastapi.testclient import TestClient
from src.main import app  # Imports your FastAPI app instance

client = TestClient(app)

def test_health_check():
    """Test to ensure the API is up and running."""
    response = client.get("/health") # Assuming you have a /health or / endpoint
    
    # We expect the server to return a 200 OK status
    assert response.status_code == 200
    
def test_fetch_cart_unauthorized():
    """Test to ensure a user without an ID cannot fetch a cart."""
    response = client.get("/")
    # If no 'x-user-id' header is provided, it should fail or return empty
    assert response.status_code in [401, 403, 422]