from backend.app.observability.request_id import get_request_id


def test_get_request_id_is_callable() -> None:
    assert callable(get_request_id)
