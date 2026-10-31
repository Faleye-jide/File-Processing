from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_csv_upload_query_and_export():
    response = client.post(
        "/api/v1/files/upload",
        files={"file": ("orders.csv", b"order_id,total\n1,12.5\n2,20\n", "text/csv")},
    )
    assert response.status_code == 201, response.text
    file_id = response.json()["id"]
    data = client.get(f"/api/v1/files/{file_id}/data").json()
    assert data["total"] == 2
    assert client.get(f"/api/v1/files/{file_id}/download?format=csv").status_code == 200


def test_unsupported():
    response = client.post("/api/v1/files/upload", files={"file": ("malware.exe", b"fake")})
    assert response.status_code == 415


def test_pdf_upload_extracts_text():
    import pymupdf

    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Hotel invoice example")
        pdf_bytes = document.tobytes()

    response = client.post(
        "/api/v1/files/upload",
        files={"file": ("hotel_bill.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    file_id = response.json()["id"]
    result = client.get(f"/api/v1/files/{file_id}/data")
    assert result.status_code == 200
    assert "Hotel invoice example" in result.json()["text"]
