from brownie import Contract


def main():
    print_monitoring_info_for_strategy("0x1aa390681036bfB47f407F26583c50ff8740A7d6")


def print_monitoring_info_for_strategy(s):
    s = Contract(s)
    want = Contract(s.want())
    yvault = Contract(s.yVault())
    maker_dai_delegate = Contract("0xf728c1645739b1d4367A94232d7473016Df908E7")

    print(f"{s.name()} deployed at {s} is using CDP {s.cdpId()}")

    shares = yvault.balanceOf(s)
    value = shares * yvault.pricePerShare() / 1e18
    debt = s.balanceOfDebt()

    print(
        f"Balance of CDP is {s.balanceOfMakerVault()/1e18:.2f} {want.symbol()} and we owe {debt/1e18:.2f} Dai"
    )
    print(f"{shares/1e18:.2f} shares in yVault worth {value/1e18:.2f} Dai")

    if value >= debt:
        print(f"Current profit is {(value - debt)/1e18:.2f} Dai")
    else:
        print(f"Current loss is {(debt - value)/1e18:.2f} Dai")

    print(
        f"Current {want.symbol()} spot price is {maker_dai_delegate.getSpotPrice(s.ilk())/1e18:.2f}"
    )
    print(f"Target collateralization ratio is {s.collateralizationRatio()/1e18:.2f}")
    print(f"Current CDP ratio is {s.getCurrentMakerVaultRatio()/1e18:.2f}")
    print(
        f"Liquidation ratio is {maker_dai_delegate.getLiquidationRatio(s.ilk())/1e27:.2f}"
    )

    if s.tendTrigger(1):
        print(
            f"Strategy is outside the tolerance band and should be rebalanced. Call tend()!"
        )
    else:
        print(f"Everything looks OK")
