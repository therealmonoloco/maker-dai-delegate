import pytest

from brownie import interface, reverts, Wei


def test_osm_reverts_should_use_spot(test_strategy, custom_osm, lib):
    test_strategy.setCustomOSM(custom_osm)
    osm = interface.IOSMedianizer(test_strategy.wantToUSDOSMProxy())

    custom_osm.setCurrentPrice(0, True)
    custom_osm.setFuturePrice(0, True)

    with reverts():
        osm.read()

    with reverts():
        osm.foresight()

    price = test_strategy._getPrice()

    assert price > 0
    assert price == lib.getSpotPrice(test_strategy.ilk())


def test_current_osm_reverts_should_use_min_future_and_spot(
    test_strategy, custom_osm, lib, RELATIVE_APPROX
):
    test_strategy.setCustomOSM(custom_osm)
    osm = interface.IOSMedianizer(test_strategy.wantToUSDOSMProxy())

    spot = lib.getSpotPrice(test_strategy.ilk())

    custom_osm.setCurrentPrice(0, True)
    with reverts():
        osm.read()

    custom_osm.setFuturePrice(spot - 1e18, False)
    assert pytest.approx(test_strategy._getPrice(), rel=RELATIVE_APPROX) == spot - 1e18
    assert (
        pytest.approx(test_strategy._getPrice(), rel=RELATIVE_APPROX)
        == osm.foresight()[0]
    )

    custom_osm.setFuturePrice(spot + 1e18, False)
    assert pytest.approx(test_strategy._getPrice(), rel=RELATIVE_APPROX) == spot
    assert test_strategy._getPrice() > 0


def test_future_osm_reverts_should_use_min_future_and_spot(
    test_strategy, custom_osm, lib, RELATIVE_APPROX
):
    test_strategy.setCustomOSM(custom_osm)
    osm = interface.IOSMedianizer(test_strategy.wantToUSDOSMProxy())

    spot = lib.getSpotPrice(test_strategy.ilk())

    custom_osm.setFuturePrice(0, True)
    with reverts():
        osm.foresight()

    custom_osm.setCurrentPrice(spot - 1e18, False)
    assert pytest.approx(test_strategy._getPrice(), rel=RELATIVE_APPROX) == spot - 1e18
    assert (
        pytest.approx(test_strategy._getPrice(), rel=RELATIVE_APPROX)
        == osm.read()[0]
    )

    custom_osm.setCurrentPrice(spot + 1e18, False)
    assert pytest.approx(test_strategy._getPrice(), rel=RELATIVE_APPROX) == spot
    assert test_strategy._getPrice() > 0


def test_get_price_should_return_min_price(
    test_strategy, custom_osm, lib, RELATIVE_APPROX
):
    test_strategy.setCustomOSM(custom_osm)
    osm = interface.IOSMedianizer(test_strategy.wantToUSDOSMProxy())

    spot = lib.getSpotPrice(test_strategy.ilk())

    custom_osm.setFuturePrice(spot + 1e18, False)
    custom_osm.setCurrentPrice(spot + 1e18, False)
    assert pytest.approx(test_strategy._getPrice(), rel=RELATIVE_APPROX) == spot

    custom_osm.setFuturePrice(spot - 1e18, False)
    custom_osm.setCurrentPrice(spot + 1e18, False)
    assert pytest.approx(test_strategy._getPrice(), rel=RELATIVE_APPROX) == spot - 1e18
    assert (
        pytest.approx(test_strategy._getPrice(), rel=RELATIVE_APPROX)
        == osm.foresight()[0]
    )

    custom_osm.setFuturePrice(spot + 1e18, False)
    custom_osm.setCurrentPrice(spot - 1e18, False)
    assert pytest.approx(test_strategy._getPrice(), rel=RELATIVE_APPROX) == spot - 1e18
    assert (
        pytest.approx(test_strategy._getPrice(), rel=RELATIVE_APPROX) == osm.read()[0]
    )
