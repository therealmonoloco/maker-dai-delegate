from brownie import reverts


def test_set_max_loss_over_max_bps_should_revert(strategy, gov):
    maxBps = 10_000

    with reverts():
        strategy.setMaxLoss(maxBps + 1, {"from": gov})


def test_set_max_loss_to_max_bps_should_not_revert(strategy, gov):
    maxBps = 10_000
    strategy.setMaxLoss(maxBps, {"from": gov})
    assert strategy.maxLoss() == maxBps


def test_set_max_loss_under_max_bps_should_not_revert(strategy, gov):
    maxBps = 10_000
    strategy.setMaxLoss(maxBps - 1, {"from": gov})
    assert strategy.maxLoss() == maxBps - 1
