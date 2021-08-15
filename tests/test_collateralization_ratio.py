import pytest
from brownie import chain


def test_lower_target_ratio_should_take_more_debt(
    vault, strategy, token, yvault, amount, user, RELATIVE_APPROX
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})

    # Harvest 1: Send funds through the strategy
    chain.sleep(1)
    strategy.harvest()

    # Shares in yVault at the current target ratio
    shares_before = yvault.balanceOf(strategy)

    new_ratio_relative = 0.8

    # In default settings this will be 250 * 0.8 = 200
    strategy.setCollateralizationRatio(
        strategy.collateralizationRatio() * new_ratio_relative
    )

    # Adjust the position
    strategy.tend()

    # Because the target collateralization ratio is lower, more DAI will be minted
    # and deposited into the yvDAI vault
    assert pytest.approx(
        shares_before / new_ratio_relative, rel=RELATIVE_APPROX
    ) == yvault.balanceOf(strategy)


def test_lower_ratio_inside_rebalancing_band_should_not_take_more_debt(
    vault, strategy, token, yvault, amount, user
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})

    # Harvest 1: Send funds through the strategy
    chain.sleep(1)
    strategy.harvest()

    # Shares in yVault at the current target ratio
    shares_before = yvault.balanceOf(strategy)

    new_ratio = strategy.collateralizationRatio() - strategy.rebalanceTolerance() + 1
    strategy.setCollateralizationRatio(new_ratio)

    # Adjust the position
    strategy.tend()

    # Because the current ratio is inside the rebalancing band
    # no more DAI will be minted and deposited into the yvDAI vault
    assert shares_before == yvault.balanceOf(strategy)


def test_higher_target_ratio_should_repay_debt(
    vault, strategy, token, yvault, amount, user, RELATIVE_APPROX
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})

    # Harvest 1: Send funds through the strategy
    chain.sleep(1)
    strategy.harvest()

    # Shares in yVault at the current target ratio
    shares_before = yvault.balanceOf(strategy)

    new_ratio_relative = 1.2

    # In default settings this will be 250 * 1.2 = 300
    strategy.setCollateralizationRatio(
        strategy.collateralizationRatio() * new_ratio_relative
    )

    # Adjust the position
    strategy.tend()

    # Because the target collateralization ratio is higher, a part of the debt
    # will be repaid to maintain a healthy ratio
    assert pytest.approx(
        shares_before / new_ratio_relative, rel=RELATIVE_APPROX
    ) == yvault.balanceOf(strategy)


def test_higher_ratio_inside_rebalancing_band_should_not_repay_debt(
    vault, test_strategy, token, yvault, amount, user
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})

    # Harvest 1: Send funds through the strategy
    chain.sleep(1)
    test_strategy.harvest()

    # Shares in yVault at the current target ratio
    shares_before = yvault.balanceOf(test_strategy)

    new_ratio = test_strategy.collateralizationRatio() + test_strategy.rebalanceTolerance() - 1
    test_strategy.setCollateralizationRatio(new_ratio)

    assert test_strategy.tendTrigger(1) == False

    # Adjust the position
    test_strategy.tend()

    # Because the current ratio is inside the rebalancing band no debt will be repaid
    assert shares_before == yvault.balanceOf(test_strategy)


def test_vault_ratio_calculation_on_withdraw(
    vault, test_strategy, token, yvault, amount, user, RELATIVE_APPROX
):
    # Initial ratio is 0 because there is no collateral locked
    assert test_strategy._getCurrentMakerVaultRatio() == 0

    # Deposit to the vault and send funds through the strategy
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    chain.sleep(1)
    test_strategy.harvest()

    # Collateral ratio should be the target ratio set
    assert (
        test_strategy._getCurrentMakerVaultRatio()
        == test_strategy.collateralizationRatio()
    )

    shares_before = yvault.balanceOf(test_strategy)

    # Withdraw 3% of the assets
    vault.withdraw(amount * 0.03, {"from": user})

    # Strategy should restore collateralization ratio to target value on withdraw
    assert (
        pytest.approx(test_strategy.collateralizationRatio(), rel=RELATIVE_APPROX)
        == test_strategy._getCurrentMakerVaultRatio()
    )

    # Strategy has less funds to invest
    assert pytest.approx(yvault.balanceOf(test_strategy), rel=RELATIVE_APPROX) == (
        shares_before * 0.97
    )


def test_tend_trigger_conditions(vault, strategy, token, amount, user, RELATIVE_APPROX):
    # Initial ratio is 0 because there is no collateral locked
    assert strategy.tendTrigger(1) == False

    # Deposit to the vault and send funds through the strategy
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    chain.sleep(1)
    strategy.harvest()

    orig_target = strategy.collateralizationRatio()
    rebalance_tolerance = strategy.rebalanceTolerance()

    # Make sure we are in equilibrium
    assert strategy.tendTrigger(1) == False

    # Going over the rebalancing band should need to adjust position
    strategy.setCollateralizationRatio(orig_target + rebalance_tolerance + 1)
    assert strategy.tendTrigger(1) == True

    # Going over the target ratio but inside rebalancing band should not adjust position
    strategy.setCollateralizationRatio(orig_target + rebalance_tolerance - 1)
    assert strategy.tendTrigger(1) == False

    # Going under the rebalancing band should need to adjust position
    strategy.setCollateralizationRatio(orig_target - rebalance_tolerance - 1)
    assert strategy.tendTrigger(1) == True

    # Going under the target ratio but inside rebalancing band should not adjust position
    strategy.setCollateralizationRatio(orig_target - rebalance_tolerance + 1)
    assert strategy.tendTrigger(1) == False
