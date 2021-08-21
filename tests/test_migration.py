import pytest

from brownie import Contract


def test_migration(
    chain,
    token,
    vault,
    strategy,
    amount,
    Strategy,
    strategist,
    gov,
    user,
    RELATIVE_APPROX,
):
    # Deposit to the vault and harvest
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    chain.sleep(1)
    strategy.harvest()
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    # migrate to a new strategy
    new_strategy = strategist.deploy(Strategy, vault)
    vault.migrateStrategy(strategy, new_strategy, {"from": gov})

    # Allow the new strategy to query the OSM proxy
    YFItoUSDOSMProxy = Contract("0x208EfCD7aad0b5DD49438E0b6A0f38E951A50E5f")
    YFItoUSDOSMProxy.set_user(new_strategy, True, {"from": gov})

    orig_cdp_id = strategy.cdpId()
    new_strategy.shiftToCdp(orig_cdp_id, {"from": gov})
    new_strategy.harvest({"from": gov})

    assert (
        pytest.approx(new_strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX)
        == amount
    )
    assert new_strategy.cdpId() == orig_cdp_id
    assert vault.strategies(new_strategy).dict()["totalDebt"] == amount


def test_yvault_migration(
    chain,
    token,
    vault,
    strategy,
    amount,
    user,
    gov,
    yvault,
    new_dai_yvault,
    dai,
    RELATIVE_APPROX,
):
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    chain.sleep(1)
    strategy.harvest()
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    balanceBefore = yvault.balanceOf(strategy) * yvault.pricePerShare() / 1e18

    strategy.migrateToNewDaiYVault(new_dai_yvault, {"from": gov})

    assert yvault.balanceOf(strategy) == 0
    assert dai.allowance(strategy, yvault) == 0
    assert dai.allowance(strategy, new_dai_yvault) == 2 ** 256 - 1
    assert (
        pytest.approx(
            new_dai_yvault.balanceOf(strategy) * new_dai_yvault.pricePerShare() / 1e18,
            rel=RELATIVE_APPROX,
        )
        == balanceBefore
    )
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount
