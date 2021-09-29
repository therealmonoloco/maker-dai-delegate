import pytest
from brownie import chain, reverts, Wei


def test_passing_zero_should_repay_all_debt(vault, strategy, token, amount, user, gov):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})

    # Send funds through the strategy
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert strategy.balanceOfDebt() > 0

    prev_collat = strategy.balanceOfMakerVault()
    strategy.emergencyDebtRepayment(0, {"from": strategy.strategist()})

    # All debt is repaid and collateral is left untouched
    assert strategy.balanceOfDebt() == 0
    assert strategy.balanceOfMakerVault() == prev_collat


def test_passing_value_over_collat_ratio_does_nothing(
    vault, strategy, token, amount, user, gov
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})

    # Send funds through the strategy
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert strategy.balanceOfDebt() > 0

    prev_debt = strategy.balanceOfDebt()
    prev_collat = strategy.balanceOfMakerVault()
    c_ratio = strategy.collateralizationRatio()
    strategy.emergencyDebtRepayment(c_ratio + 1, {"from": strategy.strategist()})

    # Debt and collat remain the same
    assert strategy.balanceOfDebt() == prev_debt
    assert strategy.balanceOfMakerVault() == prev_collat


def test_from_ratio_adjusts_debt(
    vault, strategy, token, amount, user, gov, RELATIVE_APPROX
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})

    # Send funds through the strategy
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert strategy.balanceOfDebt() > 0

    prev_debt = strategy.balanceOfDebt()
    prev_collat = strategy.balanceOfMakerVault()
    c_ratio = strategy.collateralizationRatio()
    strategy.emergencyDebtRepayment(c_ratio * 0.7, {"from": strategy.strategist()})

    # Debt is partially repaid and collateral is left untouched
    assert (
        pytest.approx(strategy.balanceOfDebt(), rel=RELATIVE_APPROX) == prev_debt * 0.7
    )
    assert strategy.balanceOfMakerVault() == prev_collat
