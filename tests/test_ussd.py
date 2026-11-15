from rotawise import ussd


def test_welcome():
    assert ussd.handle("").startswith("CON Rotawise")


def test_farm_menu_lists_plots(data_dir):
    r = ussd.handle("1")
    assert r.startswith("CON") and "Zaria" in r


def test_summary_and_best(data_dir):
    s = ussd.handle("1*1")
    assert s.startswith("CON") and "Soil tiredness" in s
    best = ussd.handle("1*1*1")
    assert best.startswith("END") and "urea" in best


def test_hausa_flow(data_dir):
    assert "Gajiyar kasa" in ussd.handle("2*1")


def test_no_data_and_invalid(data_dir):
    assert ussd.handle("1*2").startswith("END No satellite data")
    assert ussd.handle("9").startswith("END Invalid")
    assert ussd.handle("1*1*7").startswith("END")
    assert ussd.handle("1*" + "9" * 50).startswith("END Invalid")


def test_screens_fit_ussd_limit(data_dir):
    for path in ["", "1", "2", "1*1", "2*1", "1*1*1", "2*1*1", "1*1*2", "2*1*2"]:
        assert len(ussd.handle(path)) <= 4 + ussd.MAX_LEN


def test_ussd_endpoint(data_dir):
    from fastapi.testclient import TestClient

    from rotawise.api.main import app
    r = TestClient(app).post("/api/v1/ussd", data={"sessionId": "s1", "text": "1*1*1", "phoneNumber": "+234", "serviceCode": "*384#"})
    assert r.status_code == 200 and r.text.startswith("END")
