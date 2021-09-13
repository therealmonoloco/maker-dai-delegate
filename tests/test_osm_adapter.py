import pytest
from brownie import reverts


@pytest.fixture
def osmAdapter(osmProxy, whitelistedOSM, gov):
    whitelistedOSM.set_user(osmProxy, True, {"from": gov})
    yield osmProxy


def test_unauthorized_foresight_reverts(osmAdapter, user):
    with reverts("!authorized"):
        osmAdapter.foresight({"from": user})


def test_authorized_foresight_returns_price(osmAdapter, user, gov, whitelistedOSM):
    osmAdapter.setAuthorized(user, {"from": gov})

    (price, has) = osmAdapter.foresight({"from": user})

    whitelistedOSM.set_user(user, True, {"from": gov})
    (osmPrice, osmHas) = whitelistedOSM.peep({"from": user})

    assert price == osmPrice
    assert has == osmHas


def test_unauthorized_read_reverts(osmAdapter, user):
    with reverts("!authorized"):
        osmAdapter.read({"from": user})


def test_authorized_read_returns_price(osmAdapter, user, gov, whitelistedOSM):
    osmAdapter.setAuthorized(user, {"from": gov})

    (price, has) = osmAdapter.read({"from": user})

    whitelistedOSM.set_user(user, True, {"from": gov})
    (osmPrice, osmHas) = whitelistedOSM.peek({"from": user})

    assert price == osmPrice
    assert has == osmHas


def test_set_authorized_from_governance_is_allowed(osmAdapter, user, gov):
    osmAdapter.setAuthorized(user, {"from": gov})
    assert osmAdapter.authorizedStrategies(user) == True


def test_set_authorized_not_from_governance_reverts(osmAdapter, user):
    with reverts("!governance"):
        osmAdapter.setAuthorized(user, {"from": user})


def test_revoke_authorized_from_governance_is_allowed(osmAdapter, user, gov):
    osmAdapter.setAuthorized(user, {"from": gov})
    assert osmAdapter.authorizedStrategies(user) == True

    osmAdapter.revokeAuthorized(user, {"from": gov})
    assert osmAdapter.authorizedStrategies(user) == False


def test_revoke_authorized_not_from_governance_reverts(osmAdapter, user):
    with reverts("!governance"):
        osmAdapter.revokeAuthorized(user, {"from": user})


def test_can_access_read_and_foresight_after_being_authorized(osmAdapter, gov, user):
    osmAdapter.setAuthorized(user, {"from": gov})

    osmAdapter.read({"from": user})
    osmAdapter.foresight({"from": user})

    # Reaching the assert means txs did not revert
    assert True


def test_revoke_does_not_allow_to_access_read_and_foresight(osmAdapter, gov, user):
    osmAdapter.revokeAuthorized(user, {"from": gov})

    with reverts("!authorized"):
        osmAdapter.read({"from": user})

    with reverts("!authorized"):
        osmAdapter.foresight({"from": user})
