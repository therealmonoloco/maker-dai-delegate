import pytest

from brownie import chain, Wei, reverts, Contract


def test_double_init_should_revert(
    strategy,
    cloner,
    vault,
    yvault,
    strategist,
    token,
    gemJoinAdapter,
    osmProxy,
    price_oracle_usd,
    price_oracle_eth,
    gov,
):
    clone_tx = cloner.cloneMakerDaiDelegate(
        vault,
        strategist,
        strategist,
        strategist,
        yvault,
        f"StrategyMaker{token.symbol()}",
        "0x5946492d41000000000000000000000000000000000000000000000000000000",
        gemJoinAdapter,
        osmProxy,
        price_oracle_usd,
        price_oracle_eth,
    )

    cloned_strategy = Contract.from_abi(
        "Strategy", clone_tx.events["Cloned"]["clone"], strategy.abi
    )

    with reverts():
        strategy.initialize(
            vault,
            yvault,
            "NameRevert",
            "0x5946492d41000000000000000000000000000000000000000000000000000000",
            gemJoinAdapter,
            osmProxy,
            price_oracle_usd,
            price_oracle_eth,
            {"from": gov},
        )

    with reverts():
        cloned_strategy.initialize(
            vault,
            yvault,
            "NameRevert",
            "0x5946492d41000000000000000000000000000000000000000000000000000000",
            gemJoinAdapter,
            osmProxy,
            price_oracle_usd,
            price_oracle_eth,
            {"from": gov},
        )


def test_clone(
    strategy,
    cloner,
    vault,
    yvault,
    strategist,
    token,
    token_whale,
    dai,
    dai_whale,
    gemJoinAdapter,
    osmProxy,
    price_oracle_usd,
    price_oracle_eth,
    gov,
):
    clone_tx = cloner.cloneMakerDaiDelegate(
        vault,
        strategist,
        strategist,
        strategist,
        yvault,
        f"StrategyMaker{token.symbol()}",
        strategy.ilk(),
        gemJoinAdapter,
        osmProxy,
        price_oracle_usd,
        price_oracle_eth,
    )

    cloned_strategy = Contract.from_abi(
        "Strategy", clone_tx.events["Cloned"]["clone"], strategy.abi
    )

    # White-list the strategy in the OSM!
    osmProxy.setAuthorized(cloned_strategy, {"from": gov})

    vault.updateStrategyDebtRatio(strategy, 0, {"from": gov})
    vault.addStrategy(cloned_strategy, 10_000, 0, 2 ** 256 - 1, 0, {"from": gov})

    token.approve(vault, 2 ** 256 - 1, {"from": token_whale})
    vault.deposit(10 * (10 ** token.decimals()), {"from": token_whale})

    cloned_strategy.harvest({"from": gov})
    assert yvault.balanceOf(cloned_strategy) > 0

    # Sleep for 2 days
    chain.sleep(60 * 60 * 24 * 2)
    chain.mine(1)

    # Send some profit to yvDAI
    dai.transfer(yvault, Wei("100_000 ether"), {"from": dai_whale})
    cloned_strategy.harvest({"from": gov})

    assert vault.strategies(cloned_strategy).dict()["totalGain"] > 0
    assert vault.strategies(cloned_strategy).dict()["totalLoss"] == 0


def test_clone_of_clone(strategy, cloner, yvault, strategist, token, osmProxy):
    # Do not have OSM proxy for UNI - passing YFI's to test
    gemJoinUNI = Contract("0x3BC3A58b4FC1CbE7e98bB4aB7c99535e8bA9b8F1")
    token = Contract("0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984")
    yVaultUNI = Contract("0xFBEB78a723b8087fD2ea7Ef1afEc93d35E8Bed42")
    chainlinkUNIToUSD = Contract("0x553303d460EE0afB37EdFf9bE42922D8FF63220e")
    chainlinkUNIToETH = Contract("0xD6aA3D25116d8dA79Ea0246c4826EB951872e02e")

    clone_tx = cloner.cloneMakerDaiDelegate(
        yVaultUNI,
        strategist,
        strategist,
        strategist,
        yvault,
        f"StrategyMaker{token.symbol()}",
        "0x554e492d41000000000000000000000000000000000000000000000000000000",
        gemJoinUNI,
        osmProxy,
        chainlinkUNIToUSD,
        chainlinkUNIToETH,
    )

    cloned_strategy = Contract.from_abi(
        "Strategy", clone_tx.events["Cloned"]["clone"], strategy.abi
    )

    assert cloned_strategy.yVault() == yvault
    assert cloned_strategy.name() == "StrategyMakerUNI"
    assert (
        cloned_strategy.ilk()
        == "0x554e492d41000000000000000000000000000000000000000000000000000000"
    )
    assert cloned_strategy.wantToUSDOSMProxy() == osmProxy
    assert cloned_strategy.chainlinkWantToUSDPriceFeed() == chainlinkUNIToUSD
    assert cloned_strategy.chainlinkWantToETHPriceFeed() == chainlinkUNIToETH
    assert cloned_strategy.gemJoinAdapter() == gemJoinUNI
