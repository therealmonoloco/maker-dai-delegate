// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import "../interfaces/yearn/IOSMedianizer.sol";
import "../interfaces/yearn/IOSMProxy.sol";

contract YFIOSMAdapter is IOSMedianizer {
    IOSMProxy internal constant YFIOSMProxy =
        IOSMProxy(0x208EfCD7aad0b5DD49438E0b6A0f38E951A50E5f);

    address internal constant gov = 0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52;

    mapping(address => bool) public authorizedStrategies;

    function foresight()
        external
        view
        override
        returns (uint256 price, bool osm)
    {
        _onlyAuthorized();
        return YFIOSMProxy.peep();
    }

    function read() external view override returns (uint256 price, bool osm) {
        _onlyAuthorized();
        return YFIOSMProxy.peek();
    }

    function setAuthorized(address _authorized) external {
        _onlyGovernance();
        authorizedStrategies[_authorized] = true;
    }

    function revokeAuthorized(address _authorized) external {
        _onlyGovernance();
        authorizedStrategies[_authorized] = false;
    }

    function _onlyAuthorized() internal view {
        require(authorizedStrategies[msg.sender] == true, "!authorized");
    }

    function _onlyGovernance() internal view {
        require(msg.sender == gov, "!governance");
    }
}
