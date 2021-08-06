import pytest
import brownie


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

    assert (
        pytest.approx(new_strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX)
        == amount
    )
    assert new_strategy.cdpId() == orig_cdp_id


def test_shift_should_move_collateral_to_the_new_cdp(
    chain,
    token,
    vault,
    strategy,
    amount,
    Strategy,
    strategist,
    gov,
    token_whale,
    RELATIVE_APPROX,
):
    # Deposit to the vault and harvest
    token.approve(vault.address, amount, {"from": token_whale})
    vault.deposit(amount, {"from": token_whale})
    chain.sleep(1)
    strategy.harvest()
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    # migrate to a new strategy
    new_strategy = strategist.deploy(Strategy, vault)
    vault.migrateStrategy(strategy, new_strategy, {"from": gov})

    # Deposit again so the new strategy locks some collateral before migrating the cdp
    new_deposit_size = brownie.Wei("5 ether")
    token.approve(vault.address, new_deposit_size, {"from": token_whale})
    vault.deposit(new_deposit_size, {"from": token_whale})
    chain.sleep(1)
    new_strategy.harvest()

    # shiftToCdp should move any existing collateral to orig_cdp_id
    orig_cdp_id = strategy.cdpId()
    new_strategy.shiftToCdp(orig_cdp_id, {"from": gov})

    assert (
        pytest.approx(new_strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX)
        == amount + new_deposit_size
    )
    assert new_strategy.cdpId() == orig_cdp_id


def test_gov_can_shift_cdp(strategy, gov):
    # cdp-not-allowed should be the revert msg since we are shifting to a random cdp
    with brownie.reverts("cdp-not-allowed"):
        strategy.shiftToCdp(123, {"from": gov})


def test_non_gov_cannot_shift_cdp(strategy, user):
    with brownie.reverts("!authorized"):
        strategy.shiftToCdp(123, {"from": user})
