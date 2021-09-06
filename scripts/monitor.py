from brownie import Contract

import os
import requests

telegram_bot_key = os.getenv("TELEGRAM_BOT_KEY")


def main():
    output = print_monitoring_info_for_strategy(
        "0xd33535e9F2E09485aC9cE8b27F865251161065E0"
    )
    send_msg("\n".join(output))


def print_monitoring_info_for_strategy(s):
    output = ["```"]

    s = Contract(s)
    want = Contract(s.want())
    yvault = Contract(s.yVault())
    maker_dai_delegate = Contract("0xf728c1645739b1d4367A94232d7473016Df908E7")

    output.append(f"{s.name()} {s}")

    shares = yvault.balanceOf(s)
    value = shares * yvault.pricePerShare() / 1e18
    debt = s.balanceOfDebt()

    output.append(
        f"Balance of CDP #{s.cdpId()}: {s.balanceOfMakerVault()/1e18:.2f} {want.symbol()}"
    )
    output.append(f"Debt: {debt/1e18:.2f} DAI")
    output.append(f"Value of investment: {value/1e18:.2f} DAI")

    if value >= debt:
        output.append(f"Current profit: {(value - debt)/1e18:.2f} DAI")
    else:
        output.append(f"Current loss: {(debt - value)/1e18:.2f} DAI")

    output.append(
        f"{want.symbol()} price (spotter): {maker_dai_delegate.getSpotPrice(s.ilk())/1e18:.2f}"
    )
    output.append(f"Target c-ratio: {s.collateralizationRatio()/1e18:.2f}")
    output.append(f"Current c-ratio: {s.getCurrentMakerVaultRatio()/1e18:.2f}")
    output.append(
        f"Liquidation ratio: {maker_dai_delegate.getLiquidationRatio(s.ilk())/1e27:.2f}"
    )

    if s.tendTrigger(1):
        output.append(
            f"Strategy is outside the tolerance band and should be rebalanced. Call tend()!"
        )
    else:
        output.append(f"Everything looks OK")

    output.append("```")
    return output


def send_msg(text):
    payload = {"chat_id": "-1001580241915", "text": text, "parse_mode": "MarkdownV2"}
    r = requests.get(
        "https://api.telegram.org/bot" + telegram_bot_key + "/sendMessage",
        params=payload,
    )
