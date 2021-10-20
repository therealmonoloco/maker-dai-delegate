import pytest
from brownie import config, convert, interface, Contract


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


@pytest.fixture(autouse=True)
def lib(gov, MakerDaiDelegateLib):
    yield MakerDaiDelegateLib.deploy({"from": gov})


@pytest.fixture
def gov(accounts):
    yield accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)


@pytest.fixture
def user(accounts):
    yield accounts[0]


@pytest.fixture
def rewards(accounts):
    yield accounts[1]


@pytest.fixture
def guardian(accounts):
    yield accounts[2]


@pytest.fixture
def management(accounts):
    yield accounts[3]


@pytest.fixture
def strategist(accounts):
    yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)


@pytest.fixture
def keeper(accounts):
    yield accounts[5]


@pytest.fixture
def token():
    token_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # WETH
    yield Contract(token_address)


@pytest.fixture
def token_whale(accounts):
    yield accounts.at(
        "0x030bA81f1c18d280636F32af80b9AAd02Cf0854e", force=True
    )  # AAVE aWETH


@pytest.fixture
def weth_whale(accounts):
    yield accounts.at("0xC1AAE9d18bBe386B102435a8632C8063d31e747C", force=True)


@pytest.fixture
def dai():
    dai_address = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
    yield Contract(dai_address)


@pytest.fixture
def dai_whale(accounts):
    yield accounts.at("0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643", force=True)


@pytest.fixture
def borrow_token(dai):
    yield dai


@pytest.fixture
def borrow_whale(dai_whale):
    yield dai_whale


@pytest.fixture
def yvault(yvDAI):
    yield yvDAI


@pytest.fixture
def price_oracle_eth():
    # WILL NOT BE USED FOR ETH
    chainlink_oracle = interface.AggregatorInterface(
        "0x7c5d4F8345e66f68099581Db340cd65B078C41f4"
    )
    yield chainlink_oracle


@pytest.fixture
def yvDAI():
    vault_address = "0xdA816459F1AB5631232FE5e97a05BBBb94970c95"
    yield Contract(vault_address)


@pytest.fixture
def router():
    sushiswap_router = interface.ISwap("0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F")
    yield sushiswap_router


@pytest.fixture
def amount(accounts, token, user):
    amount = 10 * 10 ** token.decimals()
    # In order to get some funds for the token you are about to use,
    # it impersonate an exchange address to use it's funds.
    reserve = accounts.at("0xF977814e90dA44bFA03b6295A0616a897441aceC", force=True)
    token.transfer(user, amount, {"from": reserve})
    yield amount


@pytest.fixture
def weth():
    token_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    yield Contract(token_address)


@pytest.fixture
def weth_amount(user, weth):
    weth_amount = 10 ** weth.decimals()
    user.transfer(weth, weth_amount)
    yield weth_amount


@pytest.fixture
def vault(pm, gov, rewards, guardian, management, token):
    Vault = pm(config["dependencies"][0]).Vault
    vault = guardian.deploy(Vault)
    vault.initialize(token, gov, rewards, "", "", guardian, management)
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    vault.setManagement(management, {"from": gov})
    yield vault


@pytest.fixture
def new_dai_yvault(pm, gov, rewards, guardian, management, dai):
    Vault = pm(config["dependencies"][0]).Vault
    vault = guardian.deploy(Vault)
    vault.initialize(dai, gov, rewards, "", "", guardian, management)
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    vault.setManagement(management, {"from": gov})
    yield vault


@pytest.fixture
def osmProxy():
    # Allow the strategy to query the OSM proxy
    osm = Contract("0xCF63089A8aD2a9D8BD6Bb8022f3190EB7e1eD0f1")
    yield osm


@pytest.fixture
def gemJoinAdapter():
    gemJoin = Contract("0xF04a5cC80B1E94C69B48f5ee68a08CD2F09A7c3E")  # ETH-C
    yield gemJoin


@pytest.fixture
def healthCheck():
    yield Contract("0xDDCea799fF1699e98EDF118e0629A974Df7DF012")


@pytest.fixture
def strategy(vault, Strategy, gov, osmProxy, cloner):
    strategy = Strategy.at(cloner.original())
    strategy.setLeaveDebtBehind(False, {"from": gov})
    strategy.setDoHealthCheck(True, {"from": gov})

    # set a high acceptable max base fee to avoid changing test behavior
    strategy.setMaxAcceptableBaseFee(1500 * 1e9, {"from": gov})

    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})

    # Allow the strategy to query the OSM proxy
    osmProxy.setAuthorized(strategy, {"from": gov})
    yield strategy


@pytest.fixture
def test_strategy(
    TestStrategy,
    strategist,
    vault,
    yvault,
    token,
    gemJoinAdapter,
    osmProxy,
    price_oracle_eth,
    gov,
):
    strategy = strategist.deploy(
        TestStrategy,
        vault,
        yvault,
        f"StrategyMakerV2{token.symbol()}",
        "0x4554482d43000000000000000000000000000000000000000000000000000000",
        gemJoinAdapter,
        osmProxy,
        price_oracle_eth,
    )
    strategy.setLeaveDebtBehind(False, {"from": gov})
    strategy.setDoHealthCheck(True, {"from": gov})

    # set a high acceptable max base fee to avoid changing test behavior
    strategy.setMaxAcceptableBaseFee(1500 * 1e9, {"from": gov})

    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})

    # Allow the strategy to query the OSM proxy
    osmProxy.setAuthorized(strategy, {"from": gov})
    yield strategy


@pytest.fixture(scope="session")
def RELATIVE_APPROX():
    yield 1e-5


# Obtaining the bytes32 ilk (verify its validity before using)
# >>> ilk = ""
# >>> for i in "YFI-A":
# ...   ilk += hex(ord(i)).replace("0x","")
# ...
# >>> ilk += "0"*(64-len(ilk))
# >>>
# >>> ilk
# '5946492d41000000000000000000000000000000000000000000000000000000'
@pytest.fixture
def cloner(
    strategist,
    vault,
    yvault,
    token,
    gemJoinAdapter,
    osmProxy,
    price_oracle_eth,
    MakerDaiDelegateCloner,
):
    cloner = strategist.deploy(
        MakerDaiDelegateCloner,
        vault,
        yvault,
        f"StrategyMakerV2{token.symbol()}",
        "0x4554482d43000000000000000000000000000000000000000000000000000000",
        gemJoinAdapter,
        osmProxy,
        price_oracle_eth,
    )
    yield cloner
