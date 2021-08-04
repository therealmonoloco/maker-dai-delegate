import pytest

from brownie.convert import to_string
from brownie.network.state import TxHistory


def test_deploy_should_create_new_maker_vault(Strategy, strategist, vault):
    strategist.deploy(Strategy, vault)
    deployment_tx = TxHistory()[-1]
    assert len(deployment_tx.events["NewCdp"]) == 1


def test_cdpId_points_to_maker_vault(Strategy, strategist, vault):
    strategy = strategist.deploy(Strategy, vault)
    deployment_tx = TxHistory()[-1]
    assert strategy.cdpId() > 0
    assert strategy.cdpId() == deployment_tx.events["NewCdp"]["cdp"]


def test_maker_vault_is_owned_by_strategy(Strategy, strategist, vault):
    strategy = strategist.deploy(Strategy, vault)
    deployment_tx = TxHistory()[-1]
    assert deployment_tx.events["NewCdp"]["usr"] == strategy


# At some point the ilk should be passed to the constructor.
# Leaving this test as a sanity check.
def test_maker_vault_collateral_should_match_strategy(Strategy, strategist, vault):
    strategy = strategist.deploy(Strategy, vault)
    assert to_string(strategy.ilk()).rstrip("\x00") == "YFI-A"
