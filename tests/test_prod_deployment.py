import pytest

from brownie import reverts, chain, Contract, Wei, history, ZERO_ADDRESS
from eth_abi import encode_single


def test_prod(
    weth, dai, strategist, weth_whale, dai_whale, MakerDaiDelegateCloner, Strategy
):
    vault = Contract("0xa258C4606Ca8206D8aA700cE2143D7db854D168c")
    gov = vault.governance()
    yvault = Contract("0xdA816459F1AB5631232FE5e97a05BBBb94970c95")
    gemJoinAdapter = Contract("0xF04a5cC80B1E94C69B48f5ee68a08CD2F09A7c3E")
    osmProxy = Contract("0xCF63089A8aD2a9D8BD6Bb8022f3190EB7e1eD0f1")
    price_oracle_eth = Contract("0x7c5d4F8345e66f68099581Db340cd65B078C41f4")

    cloner = strategist.deploy(
        MakerDaiDelegateCloner,
        vault,
        yvault,
        f"StrategyMakerV2_ETH-C",
        "0x4554482d43000000000000000000000000000000000000000000000000000000",  # ETH-C
        gemJoinAdapter,
        osmProxy,
        price_oracle_eth,
    )

    original_strategy_address = history[-1].events["Deployed"]["original"]
    strategy = Strategy.at(original_strategy_address)

    assert strategy.strategist() == "0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7"
    assert strategy.keeper() == "0x736D7e3c5a6CB2CE3B764300140ABF476F6CFCCF"
    assert strategy.rewards() == "0xc491599b9A20c3A2F0A85697Ee6D9434EFa9f503"

    # White-list the strategy in the OSM!
    osmProxy.setAuthorized(strategy, {"from": gov})

    # Reduce other strategies debt allocation
    for i in range(0, 20):
        strat_address = vault.withdrawalQueue(i)
        if strat_address == ZERO_ADDRESS:
            break

        vault.updateStrategyDebtRatio(strat_address, 0, {"from": gov})

    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 0, {"from": gov})

    weth.approve(vault, 2 ** 256 - 1, {"from": weth_whale})
    vault.deposit(250 * (10 ** weth.decimals()), {"from": weth_whale})

    strategy.harvest({"from": gov})
    assert yvault.balanceOf(strategy) > 0

    print(f"After first harvest")
    print(f"strat estimatedTotalAssets: {strategy.estimatedTotalAssets()/1e18:_}")
    print(f"strat balanceOf yvDAI: {yvault.balanceOf(strategy)/1e18:_}")
    print(
        f"strat balanceOf DAI: {(yvault.balanceOf(strategy)/1e18 * yvault.pricePerShare()/1e18):_}"
    )

    # Sleep for 2 days
    chain.sleep(60 * 60 * 24 * 2)
    chain.mine(1)

    # Send some profit to yvDAI
    dai.transfer(yvault, yvault.totalDebt() * 0.02, {"from": dai_whale})
    strategy.setLeaveDebtBehind(False, {"from": gov})
    tx = strategy.harvest({"from": gov})

    print(f"After second harvest")
    print(f"strat estimatedTotalAssets: {strategy.estimatedTotalAssets()/1e18:_}")
    print(f"strat balanceOf yvDAI: {yvault.balanceOf(strategy)/1e18:_}")
    print(
        f"strat balanceOf DAI: {(yvault.balanceOf(strategy)/1e18 * yvault.pricePerShare()/1e18):_}"
    )

    assert vault.strategies(strategy).dict()["totalGain"] > 0
    assert vault.strategies(strategy).dict()["totalLoss"] == 0
    chain.sleep(60 * 60 * 8)
    chain.mine(1)

    vault.updateStrategyDebtRatio(strategy, 0, {"from": gov})
    strategy.harvest({"from": gov})

    print(f"After third harvest")
    print(f"strat estimatedTotalAssets: {strategy.estimatedTotalAssets()/1e18:_}")
    print(f"strat balanceOf yvDAI: {yvault.balanceOf(strategy)/1e18:_}")
    print(
        f"strat balanceOf DAI: {(yvault.balanceOf(strategy)/1e18 * yvault.pricePerShare()/1e18):_}"
    )
    print(f"totalLoss: {vault.strategies(strategy).dict()['totalLoss']/1e18:_}")

    assert vault.strategies(strategy).dict()["totalLoss"] < Wei("0.75 ether")
    assert vault.strategies(strategy).dict()["totalDebt"] == 0
