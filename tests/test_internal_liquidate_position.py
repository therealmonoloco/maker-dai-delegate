import pytest

from brownie import Wei


def test_liquidates_all_if_exact_same_want_balance(test_strategy, token, token_whale):
    amount = Wei("100 ether")
    token.approve(test_strategy, amount, {"from": token_whale})
    token.transfer(test_strategy, amount, {"from": token_whale})

    (_liquidatedAmount, _loss) = test_strategy._liquidatePosition(amount).return_value
    assert _liquidatedAmount == amount
    assert _loss == 0


def test_liquidates_all_if_has_more_want_balance(test_strategy, token, token_whale):
    amount = Wei("50 ether")
    token.approve(test_strategy, amount, {"from": token_whale})
    token.transfer(test_strategy, amount, {"from": token_whale})

    amountToLiquidate = amount * 0.5
    (_liquidatedAmount, _loss) = test_strategy._liquidatePosition(
        amountToLiquidate
    ).return_value
    assert _liquidatedAmount == amountToLiquidate
    assert _loss == 0


def test_liquidate_more_than_we_have_should_report_loss(
    test_strategy, token, token_whale
):
    amount = Wei("50 ether")
    token.approve(test_strategy, amount, {"from": token_whale})
    token.transfer(test_strategy, amount, {"from": token_whale})

    amountToLiquidate = amount * 1.5
    (_liquidatedAmount, _loss) = test_strategy._liquidatePosition(
        amountToLiquidate
    ).return_value
    assert _liquidatedAmount == amount
    assert _loss == (amountToLiquidate - amount)


# In this test we attempt to liquidate the whole position a week after the deposit.
# We do not simulate any gains in the yVault, so there will not be enough money
# to unlock the whole collateral without a loss.
# If leaveDebtBehind is false (default) then the strategy will need to unlock a bit
# of collateral and sell it for DAI in order to pay back the debt.
# We expect the recovered collateral to be a bit less than the deposited amount
# due to Maker Stability Fees.
def test_liquidate_position_without_enough_profit_by_selling_want(
    chain, token, vault, test_strategy, user, amount, yvault, token_whale
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})

    # sleep 7 days
    chain.sleep(24 * 60 * 60 * 7)
    chain.mine(1)

    # Simulate a loss in yvault by sending some shares away
    yvault.transfer(
        token_whale, yvault.balanceOf(test_strategy) * 0.01, {"from": test_strategy}
    )

    # Harvest so all the collateral is locked in the CDP
    test_strategy.harvest()

    (_liquidatedAmount, _loss) = test_strategy._liquidatePosition(amount).return_value
    assert _liquidatedAmount + _loss == amount
    assert _loss > 0
    assert token.balanceOf(test_strategy) < amount


# Same as above but this time leaveDebtBehind is set to True, so the strategy
# should not ever sell want. The result is the CDP being locked until new deposits
# are made and the debt set right above the floor (dust) set by Maker for YFI-A,
# which is currently 10,000 DAI
def test_liquidate_position_without_enough_profit_but_leaving_debt_behind(
    chain,
    token,
    vault,
    test_strategy,
    user,
    gov,
    amount,
    yvault,
    token_whale,
    RELATIVE_APPROX,
):
    # Make sure the strategy never sells any want
    test_strategy.setLeaveDebtBehind(True, {"from": gov})

    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})

    # sleep 7 days
    chain.sleep(24 * 60 * 60 * 7)
    chain.mine(1)

    # Harvest so all the collateral is locked in the CDP
    test_strategy.harvest()

    token_price = test_strategy._getPrice()

    # Cannot take more than dust * (collateralization ratio - tolerance) (~25,000 DAI)
    # of collateral unless we pay the full debt.
    # Here we are leaving it behind, so it's a 25k "loss" priced in want
    min_locked_collateral_for_debt_floor = (
        Wei("10_000 ether")
        / token_price
        * (
            test_strategy.collateralizationRatio() - test_strategy.rebalanceTolerance()
        )  # already in wad
    )

    # Simulate a loss in yvault by sending some shares away
    yvault.transfer(
        token_whale, yvault.balanceOf(test_strategy) * 0.01, {"from": test_strategy}
    )

    (_liquidatedAmount, _loss) = test_strategy._liquidatePosition(amount).return_value
    assert pytest.approx(_liquidatedAmount, rel=RELATIVE_APPROX) == (
        amount - min_locked_collateral_for_debt_floor
    )
    assert (
        pytest.approx(_loss, rel=RELATIVE_APPROX)
        == min_locked_collateral_for_debt_floor
    )
    assert pytest.approx(token.balanceOf(test_strategy)) == (
        amount - min_locked_collateral_for_debt_floor
    )
    assert (
        pytest.approx(token.balanceOf(test_strategy), rel=RELATIVE_APPROX)
        == amount - min_locked_collateral_for_debt_floor
    )
    # Investments are worth less
    assert test_strategy.estimatedTotalAssets() < amount


# In this test the strategy has enough profit to close the whole position
def test_happy_liquidation(
    chain, token, vault, test_strategy, yvDAI, dai, dai_whale, user, amount
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})

    # Harvest so all the collateral is locked in the CDP
    chain.sleep(1)
    test_strategy.harvest()

    # sleep 7 days
    chain.sleep(24 * 60 * 60 * 7)
    chain.mine(1)

    dai.transfer(yvDAI, yvDAI.totalAssets() * 0.01, {"from": dai_whale})

    (_liquidatedAmount, _loss) = test_strategy._liquidatePosition(amount).return_value

    assert _loss == 0
    assert _liquidatedAmount == amount
    assert test_strategy.estimatedTotalAssets() > 0
