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
    amount = Wei("200 ether")
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
    amount = Wei("200 ether")
    token.approve(test_strategy, amount, {"from": token_whale})
    token.transfer(test_strategy, amount, {"from": token_whale})

    amountToLiquidate = amount * 1.5
    (_liquidatedAmount, _loss) = test_strategy._liquidatePosition(
        amountToLiquidate
    ).return_value
    assert _liquidatedAmount == amount
    assert _loss == (amountToLiquidate - amount)


def test_liquidate_whole_position(
    chain, token, vault, test_strategy, user, amount, RELATIVE_APPROX
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})

    # sleep 7 days
    chain.sleep(24 * 60 * 60 * 7)
    chain.mine(1)

    # Harvest so all the collateral is locked in the CDP
    test_strategy.harvest()

    print(test_strategy._balanceOfDebt())
    print(test_strategy._balanceOfMakerVault())
    print(test_strategy.__valueOfInvestment())

    (_liquidatedAmount, _loss) = test_strategy._liquidatePosition(amount).return_value

    assert _liquidatedAmount == amount
    assert _loss == 0
