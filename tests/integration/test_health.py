from core.constants import JOB_HUNTER_API_TITLE


def test_health_endpoint(client):
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "message": "Service is running"}


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": JOB_HUNTER_API_TITLE}
