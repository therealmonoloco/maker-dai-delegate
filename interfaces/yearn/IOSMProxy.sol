// SPDX-License-Identifier: MIT
pragma solidity 0.6.12;

interface IOSMProxy {
    function peek() external view returns (uint256 price, bool has);

    function peep() external view returns (uint256 price, bool has);
}
