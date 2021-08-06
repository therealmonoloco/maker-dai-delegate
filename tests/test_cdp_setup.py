import pytest

from brownie.convert import to_string
from brownie.network.state import TxHistory
from brownie import chain, Wei


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


def test_dai_should_be_minted_after_depositing_collateral(
    strategy, vault, yvDAI, token, token_whale, dai
):
    # Make sure there is no balance before the first deposit
    assert yvDAI.balanceOf(strategy) == 0

    amount = 25 * (10 ** token.decimals())
    token.approve(vault.address, amount, {"from": token_whale})
    vault.deposit(amount, {"from": token_whale})

    chain.sleep(1)
    strategy.harvest()

    # Minted DAI should be deposited in yvDAI
    assert dai.balanceOf(strategy) == 0
    assert yvDAI.balanceOf(strategy) > 0


def test_minted_dai_should_match_collateralization_ratio(
    strategy, vault, yvDAI, token, token_whale, price_oracle_usd, RELATIVE_APPROX
):
    assert yvDAI.balanceOf(strategy) == 0

    # Price is returned using 8 decimals
    price = price_oracle_usd.latestAnswer() * 1e10

    amount = 25 * (10 ** token.decimals())
    token.approve(vault.address, amount, {"from": token_whale})
    vault.deposit(amount, {"from": token_whale})

    chain.sleep(1)
    strategy.harvest()

    assert pytest.approx(
        yvDAI.balanceOf(strategy) * yvDAI.pricePerShare() / 1e18, rel=RELATIVE_APPROX
    ) == (
        price
        * amount
        / (10 ** token.decimals())
        * 100
        / strategy.collateralizationRatio()
    )


def test_ethToWant_should_convert_to_yfi(strategy, price_oracle_eth, RELATIVE_APPROX):
    price = price_oracle_eth.latestAnswer()
    assert pytest.approx(
        strategy.ethToWant(Wei("1 ether")), rel=RELATIVE_APPROX
    ) == Wei("1 ether") / (price / 1e18)
    assert strategy.ethToWant(Wei(price * 420)) == Wei("420 ether")
    assert strategy.ethToWant(Wei(price * 0.5)) == Wei("0.5 ether")
