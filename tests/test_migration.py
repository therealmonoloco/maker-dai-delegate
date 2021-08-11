import pytest

from brownie import Wei, reverts


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

    orig_cdp_id = strategy.cdpId()
    new_strategy.shiftToCdp(orig_cdp_id, {"from": gov})
    new_strategy.harvest({"from": gov})

    assert (
        pytest.approx(new_strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX)
        == amount
    )
    assert new_strategy.cdpId() == orig_cdp_id
    assert vault.strategies(new_strategy).dict()["totalDebt"] == amount
