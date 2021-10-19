from brownie import chain, reverts, Contract


def test_set_collateralization_ratio_acl(
    strategy, gov, strategist, management, guardian, user
):
    strategy.setCollateralizationRatio(200 * 1e18, {"from": gov})
    assert strategy.collateralizationRatio() == 200 * 1e18

    strategy.setCollateralizationRatio(201 * 1e18, {"from": strategist})
    assert strategy.collateralizationRatio() == 201 * 1e18

    strategy.setCollateralizationRatio(202 * 1e18, {"from": management})
    assert strategy.collateralizationRatio() == 202 * 1e18

    strategy.setCollateralizationRatio(203 * 1e18, {"from": guardian})
    assert strategy.collateralizationRatio() == 203 * 1e18

    with reverts("!authorized"):
        strategy.setCollateralizationRatio(200 * 1e18, {"from": user})


def test_set_rebalance_tolerance_acl(
    strategy, gov, strategist, management, guardian, user
):
    strategy.setRebalanceTolerance(5, {"from": gov})
    assert strategy.rebalanceTolerance() == 5

    strategy.setRebalanceTolerance(4, {"from": strategist})
    assert strategy.rebalanceTolerance() == 4

    strategy.setRebalanceTolerance(3, {"from": management})
    assert strategy.rebalanceTolerance() == 3

    strategy.setRebalanceTolerance(2, {"from": guardian})
    assert strategy.rebalanceTolerance() == 2

    with reverts("!authorized"):
        strategy.setRebalanceTolerance(5, {"from": user})


def test_set_max_loss_acl(strategy, gov, strategist, management, guardian, user):
    strategy.setMaxLoss(10, {"from": gov})
    assert strategy.maxLoss() == 10

    strategy.setMaxLoss(11, {"from": management})
    assert strategy.maxLoss() == 11

    with reverts("!authorized"):
        strategy.setMaxLoss(12, {"from": strategist})

    with reverts("!authorized"):
        strategy.setMaxLoss(13, {"from": guardian})

    with reverts("!authorized"):
        strategy.setMaxLoss(14, {"from": user})


def test_set_leave_debt_behind_acl(
    strategy, gov, strategist, management, guardian, user
):
    strategy.setLeaveDebtBehind(True, {"from": gov})
    assert strategy.leaveDebtBehind() == True

    strategy.setLeaveDebtBehind(False, {"from": strategist})
    assert strategy.leaveDebtBehind() == False

    strategy.setLeaveDebtBehind(True, {"from": management})
    assert strategy.leaveDebtBehind() == True

    strategy.setLeaveDebtBehind(False, {"from": guardian})
    assert strategy.leaveDebtBehind() == False

    with reverts("!authorized"):
        strategy.setLeaveDebtBehind(True, {"from": user})


def test_switch_dex_acl(strategy, gov, strategist, management, guardian, user):
    uniswap = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
    sushiswap = "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F"

    with reverts("!authorized"):
        strategy.switchDex(True, {"from": user})

    with reverts("!authorized"):
        strategy.switchDex(True, {"from": guardian})

    with reverts("!authorized"):
        strategy.switchDex(True, {"from": strategist})

    strategy.switchDex(True, {"from": management})
    assert strategy.router() == uniswap

    strategy.switchDex(False, {"from": management})
    assert strategy.router() == sushiswap

    strategy.switchDex(True, {"from": gov})
    assert strategy.router() == uniswap

    strategy.switchDex(False, {"from": gov})
    assert strategy.router() == sushiswap


def test_shift_cdp_acl(strategy, gov, strategist, management, guardian, user):
    # cdp-not-allowed should be the revert msg when allowed / we are shifting to a random cdp
    with reverts("cdp-not-allowed"):
        strategy.shiftToCdp(123, {"from": gov})

    with reverts("!authorized"):
        strategy.shiftToCdp(123, {"from": strategist})

    with reverts("!authorized"):
        strategy.shiftToCdp(123, {"from": management})

    with reverts("!authorized"):
        strategy.shiftToCdp(123, {"from": guardian})

    with reverts("!authorized"):
        strategy.shiftToCdp(123, {"from": user})


def test_allow_managing_cdp_acl(strategy, gov, strategist, management, guardian, user):
    cdpManager = Contract("0x5ef30b9986345249bc32d8928B7ee64DE9435E39")
    cdp = strategy.cdpId()

    with reverts("!authorized"):
        strategy.grantCdpManagingRightsToUser(user, True, {"from": strategist})

    with reverts("!authorized"):
        strategy.grantCdpManagingRightsToUser(user, True, {"from": management})

    with reverts("!authorized"):
        strategy.grantCdpManagingRightsToUser(user, True, {"from": guardian})

    with reverts("!authorized"):
        strategy.grantCdpManagingRightsToUser(user, True, {"from": user})

    strategy.grantCdpManagingRightsToUser(user, True, {"from": gov})
    cdpManager.cdpAllow(cdp, guardian, 1, {"from": user})

    strategy.grantCdpManagingRightsToUser(user, False, {"from": gov})

    with reverts("cdp-not-allowed"):
        cdpManager.cdpAllow(cdp, guardian, 1, {"from": user})


def test_migrate_dai_yvault_acl(
    strategy,
    gov,
    strategist,
    management,
    guardian,
    user,
    dai,
    new_dai_yvault,
    token,
    vault,
    amount,
):
    with reverts("!authorized"):
        strategy.migrateToNewDaiYVault(new_dai_yvault, {"from": strategist})

    with reverts("!authorized"):
        strategy.migrateToNewDaiYVault(new_dai_yvault, {"from": management})

    with reverts("!authorized"):
        strategy.migrateToNewDaiYVault(new_dai_yvault, {"from": guardian})

    with reverts("!authorized"):
        strategy.migrateToNewDaiYVault(new_dai_yvault, {"from": user})

    # Need to deposit so there is something in the yVault before migrating
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    strategy.migrateToNewDaiYVault(new_dai_yvault, {"from": gov})
    assert dai.allowance(strategy, new_dai_yvault) == 2 ** 256 - 1


def test_emergency_debt_repayment_acl(
    strategy, gov, strategist, management, guardian, user
):
    strategy.emergencyDebtRepayment(0, {"from": gov})
    assert strategy.balanceOfDebt() == 0

    strategy.emergencyDebtRepayment(0, {"from": strategist})
    assert strategy.balanceOfDebt() == 0

    strategy.emergencyDebtRepayment(0, {"from": guardian})
    assert strategy.balanceOfDebt() == 0

    strategy.emergencyDebtRepayment(0, {"from": management})
    assert strategy.balanceOfDebt() == 0

    with reverts("!authorized"):
        strategy.emergencyDebtRepayment(0, {"from": user})


def test_use_chainlink_acl(strategy, gov, strategist, management, guardian, user):
    assert strategy.useChainLink() == True

    strategy.setUseChainLink(False, {"from": gov})
    assert strategy.useChainLink() == False

    strategy.setUseChainLink(True, {"from": strategist})
    assert strategy.useChainLink() == True

    strategy.setUseChainLink(False, {"from": guardian})
    assert strategy.useChainLink() == False

    strategy.setUseChainLink(True, {"from": management})
    assert strategy.useChainLink() == True

    with reverts("!authorized"):
        strategy.setUseChainLink(False, {"from": user})
