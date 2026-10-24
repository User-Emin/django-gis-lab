import json
import logging

from projectkaart.logging_config import JsonFormatter


def test_json_formatter_een_object_per_regel():
    record = logging.LogRecord(
        "kaart.x", logging.WARNING, __file__, 1, "hallo %s", ("wereld",), None
    )
    record.verzoek_id = "abc"
    regel = JsonFormatter().format(record)
    data = json.loads(regel)
    assert "\n" not in regel
    assert data["niveau"] == "WARNING"
    assert data["logger"] == "kaart.x"
    assert data["bericht"] == "hallo wereld"
    assert data["verzoek_id"] == "abc"
