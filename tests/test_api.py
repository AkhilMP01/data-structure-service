from fastapi.testclient import TestClient


def _new_dataset(client, name="Customer"):
    r = client.post("/datasets", json={"name": name})
    assert r.status_code == 201
    return r.json()["id"]


def test_create_and_retrieve_dataset(client: TestClient):
    dataset_id = _new_dataset(client, "Customer")

    r = client.post(
        f"/datasets/{dataset_id}/elements",
        json={"name": "email", "data_type": "STRING", "is_pii": True},
    )
    assert r.status_code == 201

    r = client.get(f"/datasets/{dataset_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Customer"
    assert len(body["data_elements"]) == 1
    assert body["data_elements"][0]["name"] == "email"
    assert body["data_elements"][0]["is_pii"] is True


def test_duplicate_element_rejected(client: TestClient):
    dataset_id = _new_dataset(client, "Order")

    first = client.post(
        f"/datasets/{dataset_id}/elements",
        json={"name": "status", "data_type": "STRING"},
    )
    assert first.status_code == 201

    dup = client.post(
        f"/datasets/{dataset_id}/elements",
        json={"name": "status", "data_type": "STRING"},
    )
    assert dup.status_code == 409

    # same name in a different dataset is allowed
    other_id = _new_dataset(client, "Shipment")
    ok = client.post(
        f"/datasets/{other_id}/elements",
        json={"name": "status", "data_type": "STRING"},
    )
    assert ok.status_code == 201


def test_duplicate_dataset_rejected(client: TestClient):
    assert client.post("/datasets", json={"name": "Customer"}).status_code == 201
    assert client.post("/datasets", json={"name": "Customer"}).status_code == 409


def test_invalid_data_type_rejected(client: TestClient):
    dataset_id = _new_dataset(client)
    r = client.post(
        f"/datasets/{dataset_id}/elements",
        json={"name": "age", "data_type": "NOPE"},
    )
    assert r.status_code == 422


def test_blank_dataset_name_rejected(client: TestClient):
    assert client.post("/datasets", json={"name": "   "}).status_code == 422


def test_element_on_missing_dataset(client: TestClient):
    r = client.post(
        "/datasets/999/elements",
        json={"name": "email", "data_type": "STRING"},
    )
    assert r.status_code == 404


def test_filter_elements_by_pii(client: TestClient):
    dataset_id = _new_dataset(client)
    client.post(
        f"/datasets/{dataset_id}/elements",
        json={"name": "email", "data_type": "STRING", "is_pii": True},
    )
    client.post(
        f"/datasets/{dataset_id}/elements",
        json={"name": "order_count", "data_type": "INTEGER", "is_pii": False},
    )

    r = client.get(f"/datasets/{dataset_id}/elements?is_pii=true")
    assert r.status_code == 200
    assert [e["name"] for e in r.json()] == ["email"]
