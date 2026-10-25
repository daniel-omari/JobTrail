"""Demo-only controls exist only in demo mode, so a normal run always has its defences on."""
from jobtrail import repo
from jobtrail.db import connect, init_db
from jobtrail.main import create_app


def test_normal_mode_refuses_to_turn_defences_off(client):
    assert client.get("/api/status").json()["demo"] is False
    r = client.put("/api/settings", json={"defences": False})
    assert r.status_code == 403 and "demo mode" in r.json()["detail"]
    assert client.get("/api/settings").json()["defences"] is True


def test_normal_mode_has_no_reset(client):
    assert client.post("/api/reset-scan-data?confirm=true").status_code == 404


def test_demo_mode_allows_both(make_client):
    with make_client(demo=True) as c:
        assert c.get("/api/status").json()["demo"] is True
        assert c.put("/api/settings", json={"defences": False}).json()["defences"] is False
        assert c.post("/api/reset-scan-data?confirm=true").status_code == 200


def test_normal_start_turns_defences_back_on(config):
    init_db(config.db_path)
    conn = connect(config.db_path)
    repo.put_settings(conn, {"defences": False})  # e.g. a database left over from a demo
    conn.close()
    create_app(config)
    conn = connect(config.db_path)
    assert repo.get_settings(conn)["defences"] is True
    conn.close()


def test_demo_uses_its_own_data_folder():
    from jobtrail.config import DEMO_DATA_DIR, Config
    assert Config().data_dir != DEMO_DATA_DIR
