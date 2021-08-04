import pytest

from brownie.convert import to_string


def test_cdpId_should_be_initialized_to_a_maker_vault(Strategy, strategist, vault):
    strategy = strategist.deploy(Strategy, vault)
    assert strategy.cdpId() > 0


# At some point the ilk should be passed to the constructor.
# Leaving this test as a sanity check.
def test_cdp_collateral_type_should_match_strategy(Strategy, strategist, vault):
    strategy = strategist.deploy(Strategy, vault)
    assert to_string(strategy.ilk()).rstrip("\x00") == "YFI-A"
