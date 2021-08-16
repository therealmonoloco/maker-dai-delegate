import pytest

from brownie import chain, Wei


def test_small_deposit_does_not_generate_debt_under_floor(
    vault, test_strategy, token, token_whale, yvault, borrow_token
):
    price = test_strategy._getPrice()
    floor = Wei("9_990 ether")  # assume a price floor of 10k as in YFI-A

    # Amount in want that generates 'floor' debt minus a treshold
    token_floor = ((test_strategy.collateralizationRatio() * floor / 1e18) / price) * (
        10 ** token.decimals()
    )

    # Deposit to the vault and send funds through the strategy
    token.approve(vault.address, token_floor, {"from": token_whale})
    vault.deposit(token_floor, {"from": token_whale})
    chain.sleep(1)
    test_strategy.harvest()

    # Debt floor is 10k for YFI-A, so the strategy should not take any debt
    # with a lower deposit amount
    assert yvault.balanceOf(test_strategy) == 0
    assert borrow_token.balanceOf(test_strategy) == 0

    # These are zero because all want is locked in Maker's vault
    assert token.balanceOf(test_strategy) == 0
    assert token.balanceOf(vault) == 0

    # Collateral with no debt should be a high ratio
    assert (
        test_strategy._getCurrentMakerVaultRatio()
        > test_strategy.collateralizationRatio()
    )


def test_deposit_after_passing_debt_floor_generates_debt(
    vault, test_strategy, token, token_whale, yvault, borrow_token, RELATIVE_APPROX
):
    price = test_strategy._getPrice()
    floor = Wei("9_990 ether")  # assume a price floor of 10k as in YFI-A

    # Amount in want that generates 'floor' debt minus a treshold
    token_floor = ((test_strategy.collateralizationRatio() * floor / 1e18) / price) * (
        10 ** token.decimals()
    )

    # Deposit to the vault and send funds through the strategy
    token.approve(vault.address, 2 ** 256 - 1, {"from": token_whale})
    vault.deposit(token_floor, {"from": token_whale})
    chain.sleep(1)
    test_strategy.harvest()

    # Debt floor is 10k for YFI-A, so the strategy should not take any debt
    # with a lower deposit amount
    assert yvault.balanceOf(test_strategy) == 0
    assert borrow_token.balanceOf(test_strategy) == 0

    # Deposit enough want token to go over the dust
    vault.deposit(Wei("0.5 ether"), {"from": token_whale})
    chain.sleep(1)
    test_strategy.harvest()

    # Ensure that we have now taken on debt and deposited into yVault
    assert yvault.balanceOf(test_strategy) > 0

    # Collateral with no debt should be a high ratio
    assert (
        pytest.approx(test_strategy._getCurrentMakerVaultRatio(), rel=RELATIVE_APPROX)
        == test_strategy.collateralizationRatio()
    )


def test_withdraw_does_not_leave_debt_under_floor(
    vault, test_strategy, token, token_whale, yvault
):
    # Deposit to the vault and send funds through the strategy
    token.approve(vault.address, 2 ** 256 - 1, {"from": token_whale})
    vault.deposit(Wei("10 ether"), {"from": token_whale})
    chain.sleep(1)
    test_strategy.harvest()

    # We took some debt and deposited into yvDAI
    assert yvault.balanceOf(test_strategy) > 0

    # Withdraw large amount so remaining debt is under floor
    vault.withdraw(Wei("9.9 ether"), {"from": token_whale})

    # Almost all yvDAI shares should have been used to repay the debt
    # and avoid the floor
    assert yvault.balanceOf(test_strategy) / 1e18 < 0.1

    # Because collateral balance is much larger than the debt (currently 0)
    # we expect the current ratio to be above target
    assert (
        test_strategy._getCurrentMakerVaultRatio()
        > test_strategy.collateralizationRatio()
    )


def test_large_deposit_does_not_generate_debt_over_ceiling(
    vault, test_strategy, token, token_whale, yvault, borrow_token
):
    # Deposit to the vault and send funds through the strategy
    token.approve(vault.address, 2 ** 256 - 1, {"from": token_whale})
    vault.deposit(token.balanceOf(token_whale), {"from": token_whale})
    chain.sleep(1)
    test_strategy.harvest()

    # Debt ceiling is ~7 million in YFI-A at this time
    # The whale should deposit >2x that to hit the ceiling
    assert yvault.balanceOf(test_strategy) > 0
    assert borrow_token.balanceOf(test_strategy) == 0

    # These are zero because all want is locked in Maker's vault
    assert token.balanceOf(test_strategy) == 0
    assert token.balanceOf(vault) == 0

    # Collateral ratio should be larger due to debt being capped by ceiling
    assert (
        test_strategy.collateralizationRatio() * 1.01
        < test_strategy._getCurrentMakerVaultRatio()
    )


def test_withdraw_everything_cancels_entire_debt():
    pass


def test_withdraw_under_floor_cancels_entire_debt_if_possible():
    pass


def test_withdraw_under_floor_needs_to_sell_want_to_cancel_debt():
    pass


def test_small_withdraw_cancels_corresponding_debt():
    pass
