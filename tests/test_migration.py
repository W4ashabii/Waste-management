from sqlalchemy import create_engine, inspect, text

from app.database import add_missing_columns


def test_old_database_gains_new_columns(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        # The vehicles and reports tables as they were before GPS and report history.
        conn.execute(text("CREATE TABLE vehicles (id VARCHAR(20) PRIMARY KEY, driver VARCHAR(120), capacity INTEGER, "
                          "status VARCHAR(20), note VARCHAR(255), ward INTEGER)"))
        conn.execute(text("INSERT INTO vehicles VALUES ('KMC-01', 'Ram', 5, 'Active', '', 1)"))
        conn.execute(text("CREATE TABLE reports (id INTEGER PRIMARY KEY, type VARCHAR(120), ward INTEGER, source VARCHAR(40), "
                          "date VARCHAR(20), status VARCHAR(20), route INTEGER, description TEXT, category VARCHAR(40), "
                          "location VARCHAR(200), notes JSON)"))
        added = add_missing_columns(conn)
    assert {"vehicles.lat", "vehicles.located_at", "reports.history", "reports.user_id", "reports.photo"} <= set(added)
    columns = {c["name"] for c in inspect(engine).get_columns("vehicles")}
    assert {"lat", "lng", "accuracy", "heading", "speed", "located_at"} <= columns
    with engine.begin() as conn:
        assert conn.execute(text("SELECT id, lat FROM vehicles")).all() == [("KMC-01", None)]
        assert add_missing_columns(conn) == []  # running again changes nothing
