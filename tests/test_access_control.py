import pytest

from brownie import reverts


def test_gov_can_set_collateralization_ratio(strategy, gov):
    strategy.setCollateralizationRatio(222, {"from": gov})
    assert strategy.collateralizationRatio() == 222


def test_strategist_can_set_collateralization_ratio(strategy, strategist):
    strategy.setCollateralizationRatio(200, {"from": strategist})
    assert strategy.collateralizationRatio() == 200


def test_management_can_set_collateralization_ratio(strategy, management):
    strategy.setCollateralizationRatio(200, {"from": management})
    assert strategy.collateralizationRatio() == 200


def test_guardian_can_set_collateralization_ratio(strategy, guardian):
    strategy.setCollateralizationRatio(200, {"from": guardian})
    assert strategy.collateralizationRatio() == 200


def test_non_authorized_cannot_set_collateralization_ratio(strategy, user):
    with reverts("!authorized"):
        strategy.setCollateralizationRatio(123, {"from": user})


def test_gov_can_set_rebalance_tolerance(strategy, gov):
    strategy.setRebalanceTolerance(5, {"from": gov})
    assert strategy.rebalanceTolerance() == 5


def test_strategist_can_set_rebalance_tolerance(strategy, strategist):
    strategy.setRebalanceTolerance(5, {"from": strategist})
    assert strategy.rebalanceTolerance() == 5


def test_management_can_set_rebalance_tolerance(strategy, management):
    strategy.setRebalanceTolerance(5, {"from": management})
    assert strategy.rebalanceTolerance() == 5


def test_guardian_can_set_rebalance_tolerance(strategy, guardian):
    strategy.setRebalanceTolerance(5, {"from": guardian})
    assert strategy.rebalanceTolerance() == 5


def test_non_authorized_cannot_set_rebalance_tolerance(strategy, user):
    with reverts("!authorized"):
        strategy.setRebalanceTolerance(5, {"from": user})


def test_gov_can_set_max_loss(strategy, gov):
    strategy.setMaxLoss(10, {"from": gov})
    assert strategy.maxLoss() == 10


def test_strategist_can_set_max_loss(strategy, strategist):
    strategy.setMaxLoss(10, {"from": strategist})
    assert strategy.maxLoss() == 10


def test_management_can_set_max_loss(strategy, management):
    strategy.setMaxLoss(10, {"from": management})
    assert strategy.maxLoss() == 10


def test_guardian_can_set_max_loss(strategy, guardian):
    strategy.setMaxLoss(10, {"from": guardian})
    assert strategy.maxLoss() == 10


def test_non_authorized_cannot_set_max_loss(strategy, user):
    with reverts("!authorized"):
        strategy.setMaxLoss(10, {"from": user})


def test_gov_can_set_swap_router(strategy, gov, router):
    strategy.setSwapRouter(router, {"from": gov})
    assert strategy.router() == router


def test_non_gov_cannot_set_swap_router(
    strategy, strategist, management, guardian, user, router
):
    with reverts("!authorized"):
        strategy.setSwapRouter(router, {"from": strategist})

    with reverts("!authorized"):
        strategy.setSwapRouter(router, {"from": management})

    with reverts("!authorized"):
        strategy.setSwapRouter(router, {"from": guardian})

    with reverts("!authorized"):
        strategy.setSwapRouter(router, {"from": user})


def test_gov_can_shift_cdp(strategy, gov):
    # cdp-not-allowed should be the revert msg since we are shifting to a random cdp
    with reverts("cdp-not-allowed"):
        strategy.shiftToCdp(123, {"from": gov})


def test_non_gov_cannot_shift_cdp(strategy, strategist, management, guardian, user):
    with reverts("!authorized"):
        strategy.shiftToCdp(123, {"from": strategist})

    with reverts("!authorized"):
        strategy.shiftToCdp(123, {"from": management})

    with reverts("!authorized"):
        strategy.shiftToCdp(123, {"from": guardian})

    with reverts("!authorized"):
        strategy.shiftToCdp(123, {"from": user})
