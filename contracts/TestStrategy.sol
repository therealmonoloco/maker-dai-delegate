// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import "./Strategy.sol";

contract TestStrategy is Strategy {
    constructor(address _vault) public Strategy(_vault) {}

    function _liquidatePosition(uint256 _amountNeeded)
        public
        returns (uint256 _liquidatedAmount, uint256 _loss)
    {
        (_liquidatedAmount, _loss) = liquidatePosition(_amountNeeded);
    }
}
