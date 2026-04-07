from unittest.mock import Mock, patch

from backend.monero_rpc import MoneroWalletRPC


def _mock_response(payload: dict) -> Mock:
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


@patch("backend.monero_rpc.httpx.post")
def test_generate_subaddress_uses_create_address(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response(
        {"result": {"address": "48xmrGeneratedAddress"}}
    )
    rpc = MoneroWalletRPC("http://localhost:18083", "user", "pass")

    address = rpc.generate_subaddress("trade-1")

    assert address == "48xmrGeneratedAddress"
    assert mock_post.called


@patch("backend.monero_rpc.httpx.post")
def test_get_confirmations_filters_by_address(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response(
        {
            "result": {
                "in": [
                    {"address": "other", "confirmations": 2},
                    {"address": "target", "confirmations": 11},
                    {"address": "target", "confirmations": 7},
                ]
            }
        }
    )
    rpc = MoneroWalletRPC("http://localhost:18083", "user", "pass")

    confirmations = rpc.get_confirmations("target")

    assert confirmations == 11


@patch("backend.monero_rpc.httpx.post")
def test_rpc_error_raises_runtime_error(mock_post: Mock) -> None:
    mock_post.return_value = _mock_response({"error": {"code": -1, "message": "fail"}})
    rpc = MoneroWalletRPC("http://localhost:18083", "user", "pass")

    try:
        rpc.get_version()
        assert False, "expected RuntimeError"
    except RuntimeError:
        assert True
