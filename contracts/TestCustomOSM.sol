// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import "../interfaces/yearn/IOSMedianizer.sol";

contract TestCustomOSM is IOSMedianizer {
    uint256 currentPrice;
    bool revertRead;

    uint256 futurePrice;
    bool revertForesight;

    function setCurrentPrice(uint256 _currentPrice, bool _revertRead) external {
        currentPrice = _currentPrice;
        revertRead = _revertRead;
    }

    function setFuturePrice(uint256 _futurePrice, bool _revertForesight) external {
        futurePrice = _futurePrice;
        revertForesight = _revertForesight;
    }

    function foresight()
        external
        override
        view
        returns (uint256 price, bool osm) 
    {
        if (revertForesight) {
            require (1 == 2);
        }
        return (futurePrice, true);
    }

    function read()
        external
        override
        view
        returns (uint256 price, bool osm) 
    {
        if (revertRead) {
            require (1 == 2);
        }
        return (currentPrice, true);
    }
}