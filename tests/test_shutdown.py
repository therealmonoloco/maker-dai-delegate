# TODO: Add tests that show proper operation of this strategy through "emergencyExit"
#       Make sure to demonstrate the "worst case losses" as well as the time it takes

import pytest

from brownie import Wei


def test_vault_shutdown_can_withdraw(
    chain, token, vault, test_strategy, user, amount, gov, RELATIVE_APPROX
):
    ## Deposit in Vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) == amount

    if token.balanceOf(user) > 0:
        token.transfer(
            "0x000000000000000000000000000000000000dead",
            token.balanceOf(user),
            {"from": user},
        )

    # Harvest 1: Send funds through the strategy
    chain.sleep(1)
    test_strategy.harvest({"from": gov})
    chain.sleep(3600 * 7)
    chain.mine(1)

    ## Set Emergency
    vault.setEmergencyShutdown(True)

    ## Withdraw (does it work, do you get what you expect)
    vault.withdraw({"from": user})

    assert pytest.approx(token.balanceOf(user), rel=RELATIVE_APPROX) == amount


def test_basic_shutdown(
    chain,
    token,
    vault,
    test_strategy,
    user,
    strategist,
    amount,
    yvDAI,
    dai,
    dai_whale,
    gov,
    RELATIVE_APPROX,
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) == amount

    # Harvest 1: Send funds through the strategy
    chain.sleep(1)
    test_strategy.harvest({"from": gov})
    chain.mine(100)
    assert (
        pytest.approx(test_strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX)
        == amount
    )

    ## Earn interest
    chain.sleep(3600 * 24 * 1)  ## Sleep 1 day
    chain.mine(1)

    # Send some profit to yVault
    dai.transfer(yvDAI, yvDAI.totalAssets() * 0.02, {"from": dai_whale})

    # Harvest 2: Realize profit
    test_strategy.harvest({"from": gov})
    chain.sleep(3600 * 6)  # 6 hrs needed for profits to unlock
    chain.mine(1)

    ## Make sure we are not living any debt behind (i.e: sell want if needed)
    test_strategy.setLeaveDebtBehind(False, {"from": strategist})

    ## Set emergency
    test_strategy.setEmergencyExit({"from": strategist})

    chain.sleep(1)
    test_strategy.harvest({"from": gov})  ## Remove funds from strategy

    assert vault.strategies(test_strategy).dict()["debtRatio"] == 0
    assert vault.strategies(test_strategy).dict()["totalDebt"] == 0
    assert token.balanceOf(test_strategy) / 1e18 < 0.00001  # dust
    assert token.balanceOf(vault) >= amount  ## The vault has all funds
