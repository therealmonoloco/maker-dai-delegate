import pytest

from brownie import reverts, chain, Contract, Wei, ZERO_ADDRESS
from eth_abi import encode_single


def test_ape_tax(
    weth,
    dai,
    yvault,
    cloner,
    strategy,
    strategist,
    weth_whale,
    dai_whale,
    gov,
    gemJoinAdapter,
    osmProxy,
    price_oracle_usd,
    price_oracle_eth,
):
    vault = Contract("0x5120FeaBd5C21883a4696dBCC5D123d6270637E9")
    daddy = gov
    gov = vault.governance()

    clone_tx = cloner.cloneMakerDaiDelegate(
        vault,
        strategist,
        strategist,
        strategist,
        yvault,
        f"StrategyMaker{weth.symbol()}",
        encode_single("bytes32", b"ETH-C"),
        gemJoinAdapter,
        osmProxy,
        price_oracle_usd,
        price_oracle_eth,
        {"from": strategist},
    )

    cloned_strategy = Contract.from_abi(
        "Strategy", clone_tx.events["Cloned"]["clone"], strategy.abi
    )

    # White-list the strategy in the OSM!
    osmProxy.setAuthorized(cloned_strategy, {"from": daddy})

    # Reduce other strategies debt allocation
    for i in range(0, 20):
        strat_address = vault.withdrawalQueue(i)
        if strat_address == ZERO_ADDRESS:
            break

        vault.updateStrategyDebtRatio(strat_address, 0, {"from": gov})

    vault.addStrategy(cloned_strategy, 10_000, 0, 2 ** 256 - 1, 0, {"from": gov})

    weth.approve(vault, 2 ** 256 - 1, {"from": weth_whale})
    vault.deposit(10 * (10 ** weth.decimals()), {"from": weth_whale})

    cloned_strategy.harvest({"from": gov})
    assert yvault.balanceOf(cloned_strategy) > 0

    print(f"After first harvest")
    print(
        f"strat estimatedTotalAssets: {cloned_strategy.estimatedTotalAssets()/1e18:_}"
    )
    print(f"strat balanceOf yvDAI: {yvault.balanceOf(cloned_strategy)/1e18:_}")
    print(
        f"strat balanceOf DAI: {(yvault.balanceOf(cloned_strategy)/1e18 * yvault.pricePerShare()/1e18):_}"
    )

    # Sleep for 2 days
    chain.sleep(60 * 60 * 24 * 2)
    chain.mine(1)

    # Send some profit to yvDAI
    dai.transfer(yvault, yvault.totalDebt() * 0.01, {"from": dai_whale})
    cloned_strategy.setLeaveDebtBehind(False, {"from": gov})
    tx = cloned_strategy.harvest({"from": gov})

    print(f"After second harvest")
    print(
        f"strat estimatedTotalAssets: {cloned_strategy.estimatedTotalAssets()/1e18:_}"
    )
    print(f"strat balanceOf yvDAI: {yvault.balanceOf(cloned_strategy)/1e18:_}")
    print(
        f"strat balanceOf DAI: {(yvault.balanceOf(cloned_strategy)/1e18 * yvault.pricePerShare()/1e18):_}"
    )

    assert vault.strategies(cloned_strategy).dict()["totalGain"] > 0
    assert vault.strategies(cloned_strategy).dict()["totalLoss"] == 0
    chain.sleep(60 * 60 * 8)
    chain.mine(1)

    vault.updateStrategyDebtRatio(cloned_strategy, 0, {"from": gov})
    cloned_strategy.harvest({"from": gov})

    print(f"After third harvest")
    print(
        f"strat estimatedTotalAssets: {cloned_strategy.estimatedTotalAssets()/1e18:_}"
    )
    print(f"strat balanceOf yvDAI: {yvault.balanceOf(cloned_strategy)/1e18:_}")
    print(
        f"strat balanceOf DAI: {(yvault.balanceOf(cloned_strategy)/1e18 * yvault.pricePerShare()/1e18):_}"
    )
    print(f"totalLoss: {vault.strategies(cloned_strategy).dict()['totalLoss']/1e18:_}")

    assert vault.strategies(cloned_strategy).dict()["totalLoss"] < Wei("0.5 ether")
    assert vault.strategies(cloned_strategy).dict()["totalDebt"] == 0
