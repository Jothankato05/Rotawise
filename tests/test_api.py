from fastapi.testclient import TestClient


def client():
    from rotawise.api.main import _cached_analysis, app
    _cached_analysis.cache_clear()
    return TestClient(app)


def test_health_and_ready(data_dir):
    c = client()
    assert c.get("/api/v1/health").json()["status"] == "ok"
    r = c.get("/api/v1/ready").json()
    assert r["plots"] == 5 and r["plots_with_data"] == 1


def test_security_headers_and_request_id(data_dir):
    r = client().get("/api/v1/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert "Content-Security-Policy" in r.headers
    assert len(r.headers["X-Request-ID"]) > 8


def test_plots_list(data_dir):
    plots = client().get("/api/v1/plots").json()["plots"]
    assert {p["id"]: p["has_data"] for p in plots}["101"] is True


def test_advice_ok_and_prices_applied(data_dir):
    c = client()
    r = c.get("/api/v1/plots/101/advice", params={"urea_price": 60000})
    assert r.status_code == 200
    assert r.json()["rotations"]["prices_used"]["urea_ngn_per_bag"] == 60000


def test_advice_errors(data_dir):
    c = client()
    assert c.get("/api/v1/plots/999/advice").status_code == 404
    assert c.get("/api/v1/plots/102/advice").status_code == 409
    assert c.get("/api/v1/plots/..%2F..%2Fetc/advice").status_code in (404, 422)
    assert c.get("/api/v1/plots/101/advice", params={"urea_price": -5}).status_code == 422
    assert c.get("/api/v1/plots/101/advice", params={"lang": "fr"}).status_code == 422


def test_hausa_labels(data_dir):
    r = client().get("/api/v1/plots/101/advice", params={"lang": "ha"}).json()
    labels = {lbl for o in r["rotations"]["options"] for lbl in o["sequence_labels"]}
    assert "Masara" in labels


def test_metrics(data_dir):
    c = client()
    c.get("/api/v1/plots")
    assert "rotawise_http_requests_total" in c.get("/metrics").text


def test_rate_limit():
    from rotawise.api.middleware import TokenBucket
    b = TokenBucket(rate_per_min=60, burst=3)
    assert [b.allow("x") for _ in range(4)] == [True, True, True, False]
    assert b.allow("y")
