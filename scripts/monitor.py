from brownie import Contract

import os
import requests

telegram_bot_key = os.getenv("TELEGRAM_BOT_KEY")


def main():
    output = print_monitoring_info_for_strategy(
        "0x1aa390681036bfB47f407F26583c50ff8740A7d6"
    )
    send_msg("\n".join(output))


def print_monitoring_info_for_strategy(s):
    output = []

    s = Contract(s)
    want = Contract(s.want())
    yvault = Contract(s.yVault())
    maker_dai_delegate = Contract("0xf728c1645739b1d4367A94232d7473016Df908E7")

    output.append(f"{s.name()} deployed at {s} is using CDP {s.cdpId()}")

    shares = yvault.balanceOf(s)
    value = shares * yvault.pricePerShare() / 1e18
    debt = s.balanceOfDebt()

    output.append(
        f"Balance of CDP is {s.balanceOfMakerVault()/1e18:.2f} {want.symbol()} and we owe {debt/1e18:.2f} Dai"
    )
    output.append(f"{shares/1e18:.2f} shares in yVault worth {value/1e18:.2f} Dai")

    if value >= debt:
        output.append(f"Current profit is {(value - debt)/1e18:.2f} Dai")
    else:
        output.append(f"Current loss is {(debt - value)/1e18:.2f} Dai")

    output.append(
        f"{want.symbol()} price from the spotter is {maker_dai_delegate.getSpotPrice(s.ilk())/1e18:.2f}"
    )
    output.append(
        f"Target collateralization ratio is {s.collateralizationRatio()/1e18:.2f}"
    )
    output.append(f"Current CDP ratio is {s.getCurrentMakerVaultRatio()/1e18:.2f}")
    output.append(
        f"Liquidation ratio is {maker_dai_delegate.getLiquidationRatio(s.ilk())/1e27:.2f}"
    )

    if s.tendTrigger(1):
        output.append(
            f"*Strategy is outside the tolerance band and should be rebalanced. Call tend()!*"
        )
    else:
        output.append(f"Everything looks OK")
    return output


def send_msg(text):
    payload = {"chat_id": "-1001580241915", "text": text}
    r = requests.get(
        "https://api.telegram.org/bot" + telegram_bot_key + "/sendMessage",
        params=payload,
    )
