import io
import json

import pandas as pd
import pymupdf


def test_health_and_dashboard(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/").status_code == 200


def test_csv_upload_query_export_and_original(client):
    content = b"order_id,total\n1,12.5\n2,20\n"
    response = client.post("/api/v1/files/upload", files={"file": ("orders.csv", content, "text/csv")})
    assert response.status_code == 201, response.text
    body = response.json()
    file_id = body["id"]
    assert body["rows_count"] == 2

    metadata = client.get(f"/api/v1/files/{file_id}").json()
    assert metadata["file_size_bytes"] == len(content)
    assert "original_content" not in metadata
    assert len(metadata["sha256"]) == 64
    assert client.get("/api/v1/files").json()[0]["id"] == file_id

    data = client.get(f"/api/v1/files/{file_id}/data?limit=1&offset=1").json()
    assert data["total"] == 2
    assert data["records"] == [{"order_id": 2, "total": 20.0}]
    assert client.get(f"/api/v1/files/{file_id}/original").content == content
    csv_export = client.get(f"/api/v1/files/{file_id}/download?format=csv")
    assert csv_export.status_code == 200
    assert "order_id,total" in csv_export.text
    json_export = client.get(f"/api/v1/files/{file_id}/download?format=json")
    assert json_export.json()["records"][0]["order_id"] == 1


def test_json_upload(client):
    payload = [{"product": "tea", "qty": 2}, {"product": "milk", "qty": 1}]
    response = client.post(
        "/api/v1/files/upload",
        files={"file": ("items.json", json.dumps(payload).encode(), "application/json")},
    )
    assert response.status_code == 201, response.text
    data = client.get(f"/api/v1/files/{response.json()['id']}/data").json()
    assert data["records"] == payload


def test_excel_upload(client):
    bio = io.BytesIO()
    pd.DataFrame([{"merchant": "Cafe", "amount": 8.25}]).to_excel(bio, index=False)
    response = client.post(
        "/api/v1/files/upload",
        files={"file": ("expense.xlsx", bio.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 201, response.text
    data = client.get(f"/api/v1/files/{response.json()['id']}/data").json()
    assert data["records"] == [{"merchant": "Cafe", "amount": 8.25}]


def test_pdf_upload_extracts_text_and_stores_original(client):
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Hotel invoice example")
        pdf_bytes = document.tobytes()

    response = client.post("/api/v1/files/upload", files={"file": ("hotel_bill.pdf", pdf_bytes, "application/pdf")})
    assert response.status_code == 201, response.text
    file_id = response.json()["id"]
    assert response.json()["rows_count"] is None
    data = client.get(f"/api/v1/files/{file_id}/data").json()
    assert "Hotel invoice example" in data["text"]
    assert data["page_count"] == 1
    assert client.get(f"/api/v1/files/{file_id}/original").content == pdf_bytes
    assert "Hotel invoice example" in client.get(f"/api/v1/files/{file_id}/download?format=json").text
    assert client.get(f"/api/v1/files/{file_id}/download?format=csv").status_code == 422


def test_rejects_bad_content_and_missing_file(client):
    assert client.post("/api/v1/files/upload", files={"file": ("malware.exe", b"fake")}).status_code == 415
    assert client.post("/api/v1/files/upload", files={"file": ("bad.json", b'{}')}).status_code == 422
    assert client.post("/api/v1/files/upload", files={"file": ("scan.pdf", b'not a pdf')}).status_code == 422
    assert client.get("/api/v1/files/non-existent").status_code == 404
    assert client.get("/api/v1/files/non-existent/original").status_code == 404
    assert client.get("/api/v1/files?limit=0").status_code == 422
    assert client.get("/api/v1/files/non-existent/download?format=xml").status_code == 422


def test_each_upload_is_persisted_separately(client):
    for name in ["first.csv", "second.csv"]:
        response = client.post("/api/v1/files/upload", files={"file": (name, b"id\n1\n", "text/csv")})
        assert response.status_code == 201
    listed = client.get("/api/v1/files").json()
    assert len(listed) == 2
    assert listed[0]["id"] != listed[1]["id"]
