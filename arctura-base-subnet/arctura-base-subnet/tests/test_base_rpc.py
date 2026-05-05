"""tests/test_base_rpc.py — Base RPC client tests (mocked)."""
import json
import pytest
from unittest.mock import MagicMock, patch
from arctura_base.base_rpc import BaseRPCClient


@pytest.fixture
def mock_client():
    with patch("arctura_base.base_rpc.Web3") as MockWeb3:
        w3 = MagicMock()
        w3.is_connected.return_value = True
        w3.eth.chain_id = 8453
        MockWeb3.return_value = w3
        MockWeb3.HTTPProvider.return_value = MagicMock()
        MockWeb3.to_checksum_address.side_effect = lambda x: x
        client = BaseRPCClient(rpc_url="http://mock")
        client.w3 = w3
        yield client


def test_get_balance_native(mock_client):
    mock_client.w3.eth.get_balance.return_value = 1_000_000_000_000_000_000
    mock_client.w3.eth.block_number = 21_000_000
    result = mock_client.get_balance("0xAbc", block_number=21_000_000)
    assert result["balance"] == 1_000_000_000_000_000_000
    assert result["block_number"] == 21_000_000
    assert result["token"] is None


def test_unknown_query_type_raises(mock_client):
    with pytest.raises(ValueError, match="Unknown query_type"):
        mock_client.execute_mandate(
            query_type="invalid_type",
            contract_address=None,
            block_range=(0, 0),
            payload={},
        )
