// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import {BaseStrategy} from "@yearnvaults/contracts/BaseStrategy.sol";
import "@openzeppelin/contracts/math/Math.sol";
import {
    SafeERC20,
    SafeMath,
    IERC20,
    Address
} from "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

import "./libraries/MakerDaiDelegateLib.sol";

import "../interfaces/chainlink/AggregatorInterface.sol";
import "../interfaces/maker/IMaker.sol";
import "../interfaces/swap/ISwap.sol";
import "../interfaces/yearn/IVault.sol";

contract Strategy is BaseStrategy {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    // Units used in Maker contracts
    uint256 internal constant WAD = 10**18;
    uint256 internal constant RAY = 10**27;

    // Maker vaults manager
    ManagerLike internal constant cdpManager =
        ManagerLike(0x5ef30b9986345249bc32d8928B7ee64DE9435E39);

    // Part of the Maker Rates Module in charge of accumulating stability fees
    JugLike internal constant jug =
        JugLike(0x19c0976f590D67707E62397C87829d896Dc0f1F1);

    // Debt Ceiling Instant Access Module
    DssAutoLine internal constant autoLine =
        DssAutoLine(0xC7Bdd1F2B16447dcf3dE045C4a039A60EC2f0ba3);

    // Token Adapter Module for collateral
    DaiJoinLike internal constant daiJoinAdapter =
        DaiJoinLike(0x9759A6Ac90977b93B58547b4A71c78317f391A28);

    // Token Adapter Module for collateral
    GemJoinLike internal constant gemJoinAdapter =
        GemJoinLike(0x3ff33d9162aD47660083D7DC4bC02Fb231c81677);

    // Liaison between oracles and core Maker contracts
    SpotLike internal constant spotter =
        SpotLike(0x65C79fcB50Ca1594B025960e539eD7A9a6D434A3);

    // Maker Accounting System
    VatLike internal vat;

    // Maker Oracle Security Module
    OracleSecurityModule public constant YFItoUSDOSMProxy =
        OracleSecurityModule(0x208EfCD7aad0b5DD49438E0b6A0f38E951A50E5f);

    // Use Chainlink oracle to obtain latest YFI/ETH price
    AggregatorInterface internal constant chainlinkYFItoETHPriceFeed =
        AggregatorInterface(0x7c5d4F8345e66f68099581Db340cd65B078C41f4);

    // Use Chainlink oracle to obtain latest YFI/USD price
    AggregatorInterface internal constant chainlinkYFItoUSDPriceFeed =
        AggregatorInterface(0xA027702dbb89fbd58938e4324ac03B58d812b0E1);

    // DAI yVault
    IVault public yVault = IVault(0xdA816459F1AB5631232FE5e97a05BBBb94970c95);

    // DAI token
    IERC20 internal constant investmentToken =
        IERC20(0x6B175474E89094C44Da98b954EedeAC495271d0F);

    // 100%
    uint256 internal constant MAX_BPS = WAD;

    // Wrapped Ether - Used for swaps routing
    address internal constant WETH = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;

    // SushiSwap router
    ISwap public router = ISwap(0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F);

    // Collateral type
    bytes32 public ilk = "YFI-A";

    // Our vault identifier
    uint256 public cdpId;

    // Our desired collaterization ratio
    uint256 public collateralizationRatio;

    // Allow the collateralization ratio to drift a bit in order to avoid cycles
    uint256 public rebalanceTolerance;

    // Maximum acceptable lost on withdrawal. Default to 0.01%.
    uint256 public maxLoss = 1;

    // If set to true the strategy will never try to repay debt by selling want
    bool public leaveDebtBehind;

    constructor(address _vault) public BaseStrategy(_vault) {
        cdpId = cdpManager.open(ilk, address(this));
        vat = VatLike(cdpManager.vat());

        // Minimum collaterization ratio on YFI-A is 175%
        // Use 250% as target
        collateralizationRatio = (250 * MAX_BPS) / 100;

        // Current ratio can drift (collateralizationRatio - rebalanceTolerance, collateralizationRatio + rebalanceTolerance)
        // Allow additional 5% in any direction (245, 255) by default
        rebalanceTolerance = (5 * MAX_BPS) / 100;

        // If we lose money in yvDAI then we are OK selling want to repay it
        leaveDebtBehind = false;
    }

    // ----------------- SETTERS & MIGRATION -----------------

    // Target collateralization ratio to maintain within bounds
    function setCollateralizationRatio(uint256 _collateralizationRatio)
        external
        onlyEmergencyAuthorized
    {
        collateralizationRatio = _collateralizationRatio;
    }

    // Rebalancing bands (collat ratio - tolerance, collat_ratio + tolerance)
    function setRebalanceTolerance(uint256 _rebalanceTolerance)
        external
        onlyEmergencyAuthorized
    {
        rebalanceTolerance = _rebalanceTolerance;
    }

    // Max slippage to accept when withdrawing from yVault
    function setMaxLoss(uint256 _maxLoss) external onlyEmergencyAuthorized {
        maxLoss = _maxLoss;
    }

    // If set to true the strategy will never sell want to repay debts
    function setLeaveDebtBehind(bool _leaveDebtBehind)
        external
        onlyEmergencyAuthorized
    {
        leaveDebtBehind = _leaveDebtBehind;
    }

    // Where to route token swaps
    // Access control is stricter in this method as it will be sent funds
    function setSwapRouter(ISwap _router) external onlyGovernance {
        router = _router;
    }

    // Required to move funds to a new cdp and use a different cdpId after migration
    // Should only be called by governance as it will move funds
    function shiftToCdp(uint256 newCdpId) external onlyGovernance {
        cdpManager.shift(cdpId, newCdpId);
        cdpId = newCdpId;
    }

    // Move yvDAI funds to a new yVault
    function migrateToNewDaiYVault(IVault newYVault) external onlyGovernance {
        yVault.withdraw(
            yVault.balanceOf(address(this)),
            address(this),
            maxLoss
        );
        investmentToken.safeApprove(address(yVault), 0);
        investmentToken.safeApprove(address(newYVault), type(uint256).max);
        newYVault.deposit();

        yVault = newYVault;
    }

    // ******** OVERRIDE THESE METHODS FROM BASE CONTRACT ************

    function name() external view override returns (string memory) {
        return "StrategyMakerYFI";
    }

    function delegatedAssets() external view override returns (uint256) {
        return _convertInvestmentTokenToWant(_valueOfInvestment());
    }

    function estimatedTotalAssets() public view override returns (uint256) {
        return
            balanceOfWant()
                .add(balanceOfMakerVault())
                .add(_convertInvestmentTokenToWant(balanceOfInvestmentToken()))
                .add(_convertInvestmentTokenToWant(_valueOfInvestment()))
                .sub(_convertInvestmentTokenToWant(balanceOfDebt()));
    }

    function prepareReturn(uint256 _debtOutstanding)
        internal
        override
        returns (
            uint256 _profit,
            uint256 _loss,
            uint256 _debtPayment
        )
    {
        uint256 totalDebt = vault.strategies(address(this)).totalDebt;

        // Claim rewards from yVault
        _takeYVaultProfit();

        uint256 totalAssetsAfterProfit = estimatedTotalAssets();

        _profit = totalAssetsAfterProfit > totalDebt
            ? totalAssetsAfterProfit.sub(totalDebt)
            : 0;

        uint256 _amountFreed;
        (_amountFreed, _loss) = liquidatePosition(
            _debtOutstanding.add(_profit)
        );
        _debtPayment = Math.min(_debtOutstanding, _amountFreed);

        if (_loss > _profit) {
            // Example:
            // debtOutstanding 100, profit 50, _amountFreed 100, _loss 50
            // loss should be 0, (50-50)
            // profit should endup in 0
            _loss = _loss.sub(_profit);
            _profit = 0;
        } else {
            // Example:
            // debtOutstanding 100, profit 50, _amountFreed 140, _loss 10
            // _profit should be 40, (50 profit - 10 loss)
            // loss should end up in be 0
            _profit = _profit.sub(_loss);
            _loss = 0;
        }
    }

    function adjustPosition(uint256 _debtOutstanding) internal override {
        _keepBasicMakerHygiene();

        // If we have enough want to deposit more into the maker vault, we do it
        // Do not skip the rest of the function as it may need to repay or take on more debt
        uint256 wantBalance = balanceOfWant();
        if (wantBalance > _debtOutstanding) {
            uint256 amountToDeposit = wantBalance.sub(_debtOutstanding);
            _depositToMakerVault(amountToDeposit);
        }

        // Allow the ratio to move a bit in either direction to avoid cycles
        uint256 currentRatio = getCurrentMakerVaultRatio();
        if (currentRatio < collateralizationRatio.sub(rebalanceTolerance)) {
            _repayDebt(currentRatio);
        } else if (
            currentRatio > collateralizationRatio.add(rebalanceTolerance)
        ) {
            _mintMoreInvestmentToken();
        }

        // If we have anything left to invest then deposit into the yVault
        uint256 balanceIT = balanceOfInvestmentToken();
        if (balanceIT > 0) {
            _checkAllowance(
                address(yVault),
                address(investmentToken),
                balanceIT
            );

            yVault.deposit();
        }
    }

    function liquidatePosition(uint256 _amountNeeded)
        internal
        override
        returns (uint256 _liquidatedAmount, uint256 _loss)
    {
        uint256 balance = balanceOfWant();

        // Check if we can handle it without freeing collateral
        if (balance >= _amountNeeded) {
            return (_amountNeeded, 0);
        }

        // We only need to free the amount of want not readily available
        uint256 amountToFree = _amountNeeded.sub(balance);

        uint256 price = _getWantTokenPrice();
        uint256 collateralBalance = balanceOfMakerVault();

        // We cannot free more than what we have locked
        amountToFree = Math.min(amountToFree, collateralBalance);

        uint256 totalDebt = balanceOfDebt();

        // If for some reason we do not have debt, make sure the operation does not revert
        if (totalDebt == 0) {
            totalDebt = 1;
        }

        uint256 toFreeIT = amountToFree.mul(price).div(WAD);
        uint256 collateralIT = collateralBalance.mul(price).div(WAD);
        uint256 newRatio =
            collateralIT.sub(toFreeIT).mul(MAX_BPS).div(totalDebt);

        // Attempt to repay necessary debt to restore the target collateralization ratio
        _repayDebt(newRatio);

        // Unlock as much collateral as possible while keeping the target ratio
        amountToFree = Math.min(amountToFree, _maxWithdrawal());
        _freeCollateralAndRepayDai(amountToFree, 0);

        // If we are liquidating all positions and were not able to pay the debt in full,
        // we may need to unlock some collateral to sell
        if (
            _amountNeeded > amountToFree &&
            balanceOfDebt() > 0 &&
            !leaveDebtBehind
        ) {
            uint256 currentInvestmentValue = _valueOfInvestment();

            // Very small numbers may round to 0 'want' to use for buying investment token
            // Enforce a minimum of $1 to swap in order to avoid this
            uint256 investmentLeftToAcquire =
                balanceOfDebt().add(WAD).sub(currentInvestmentValue);

            uint256 investmentLeftToAcquireInWant =
                _convertInvestmentTokenToWant(investmentLeftToAcquire);

            if (investmentLeftToAcquireInWant <= balanceOfWant()) {
                _buyInvestmentTokenWithWant(investmentLeftToAcquire);
                _repayDebt(0);
                _freeCollateralAndRepayDai(balanceOfMakerVault(), 0);
            }
        }

        uint256 looseWant = balanceOfWant();
        if (_amountNeeded > looseWant) {
            _liquidatedAmount = looseWant;
            _loss = _amountNeeded.sub(looseWant);
        } else {
            _liquidatedAmount = _amountNeeded;
        }
    }

    function liquidateAllPositions()
        internal
        override
        returns (uint256 _amountFreed)
    {
        (_amountFreed, ) = liquidatePosition(estimatedTotalAssets());
    }

    function tendTrigger(uint256 callCostInWei)
        public
        view
        override
        returns (bool)
    {
        // Nothing to adjust if there is no collateral locked
        if (balanceOfMakerVault() == 0) {
            return false;
        }

        uint256 currentRatio = getCurrentMakerVaultRatio();

        // If we need to repay debt or mint more DAI and are outside the tolerance bands,
        // we do it regardless of the call cost
        return
            (currentRatio < collateralizationRatio.sub(rebalanceTolerance)) ||
            (currentRatio > collateralizationRatio.add(rebalanceTolerance));
    }

    function prepareMigration(address _newStrategy) internal override {
        // Transfer Maker Vault ownership to the new startegy
        cdpManager.give(cdpId, _newStrategy);

        // Move yvDAI balance to the new strategy
        IERC20(yVault).safeTransfer(
            _newStrategy,
            yVault.balanceOf(address(this))
        );
    }

    function protectedTokens()
        internal
        view
        override
        returns (address[] memory)
    {
        address[] memory protected = new address[](2);
        protected[0] = address(investmentToken);
        protected[1] = address(yVault);
        return protected;
    }

    function ethToWant(uint256 _amtInWei)
        public
        view
        virtual
        override
        returns (uint256)
    {
        // YFI price in ETH with 18 decimals
        uint256 price = uint256(chainlinkYFItoETHPriceFeed.latestAnswer());
        return _amtInWei.mul(WAD).div(price);
    }

    // ----------------- INTERNAL FUNCTIONS SUPPORT -----------------

    // Make sure we update some key content in Maker contracts
    // These can be updated by anyone without authenticating
    function _keepBasicMakerHygiene() internal {
        // Update accumulated stability fees
        jug.drip(ilk);

        // Update the debt ceiling using DSS Auto Line
        autoLine.exec(ilk);
    }

    function _repayDebt(uint256 currentRatio) internal {
        uint256 currentDebt = balanceOfDebt();

        // Nothing to repay if we are over the collateralization ratio
        // or there is no debt
        if (currentRatio > collateralizationRatio || currentDebt == 0) {
            return;
        }

        // ratio = collateral / debt
        // collateral = current_ratio * current_debt
        // collateral amount is invariant here so we want to find new_debt
        // so that new_debt * desired_ratio = current_debt * current_ratio
        // new_debt = current_debt * current_ratio / desired_ratio
        // and the amount to repay is the difference between current_debt and new_debt
        uint256 newDebt =
            currentDebt.mul(currentRatio).div(collateralizationRatio);

        uint256 amountToRepay;

        // Maker will revert if the outstanding debt is less than a debt floor
        // called 'dust'. If we are there we need to either pay the debt in full
        // or leave at least 'dust' balance (10,000 DAI for YFI-A)
        uint256 debtFloor = MakerDaiDelegateLib.debtFloor(vat, ilk);
        if (newDebt <= debtFloor) {
            // If we sold want to repay debt we will have DAI readily available in the strategy
            // This means we need to count both yvDAI shares and current DAI balance
            uint256 totalInvestmentAvailableToRepay =
                _valueOfInvestment().add(balanceOfInvestmentToken());

            if (totalInvestmentAvailableToRepay >= currentDebt) {
                // Pay the entire debt if we have enough investment token
                amountToRepay = currentDebt;
            } else {
                // Pay just 0.1 cent above debtFloor (best effort without liquidating want)
                amountToRepay = currentDebt.sub(debtFloor).sub(1e15);
            }
        } else {
            // If we are not near the debt floor then just pay the exact amount
            // needed to obtain a healthy collateralization ratio
            amountToRepay = currentDebt.sub(newDebt);
        }

        uint256 balanceIT = balanceOfInvestmentToken();
        if (amountToRepay > balanceIT) {
            _withdrawFromYVault(amountToRepay.sub(balanceIT));
        }
        _repayInvestmentTokenDebt(amountToRepay);
    }

    // Mint the maximum DAI possible for the locked collateral
    function _mintMoreInvestmentToken() internal {
        uint256 price = _getWantTokenPrice();
        uint256 amount = balanceOfMakerVault();

        uint256 daiToMint =
            amount.mul(price).mul(MAX_BPS).div(collateralizationRatio).div(WAD);
        daiToMint = daiToMint.sub(balanceOfDebt());
        _lockCollateralAndMintDai(0, daiToMint);
    }

    function _withdrawFromYVault(uint256 _amountIT) internal returns (uint256) {
        if (_amountIT == 0) {
            return 0;
        }
        // No need to check allowance because the contract == token
        uint256 balancePrior = balanceOfInvestmentToken();
        uint256 sharesToWithdraw =
            Math.min(
                _investmentTokenToYShares(_amountIT),
                yVault.balanceOf(address(this))
            );
        if (sharesToWithdraw == 0) {
            return 0;
        }
        yVault.withdraw(sharesToWithdraw, address(this), maxLoss);
        return balanceOfInvestmentToken().sub(balancePrior);
    }

    function _repayInvestmentTokenDebt(uint256 amount) internal {
        if (amount == 0) {
            return;
        }

        uint256 debt = balanceOfDebt();
        uint256 balanceIT = balanceOfInvestmentToken();

        // We cannot pay more than loose balance
        amount = Math.min(amount, balanceIT);

        // We cannot pay more than we owe
        amount = Math.min(amount, debt);

        _checkAllowance(
            address(daiJoinAdapter),
            address(investmentToken),
            amount
        );

        if (amount > 0) {
            // When repaying the full debt it is very common to experience Vat/dust
            // reverts due to the debt being non-zero and less than the debt floor.
            // This can happen due to rounding when _wipeAndFreeGem() divides
            // the DAI amount by the accumulated stability fee rate.
            // To circumvent this issue we will add 1 Wei to the amount to be paid
            // if there is enough investment token balance (DAI) to do it.
            if (debt.sub(amount) == 0 && balanceIT.sub(amount) >= 1) {
                amount = amount.add(1);
            }

            // Repay debt amount without unlocking collateral
            _freeCollateralAndRepayDai(0, amount);
        }
    }

    function _checkAllowance(
        address _contract,
        address _token,
        uint256 _amount
    ) internal {
        if (IERC20(_token).allowance(address(this), _contract) < _amount) {
            IERC20(_token).safeApprove(_contract, 0);
            IERC20(_token).safeApprove(_contract, type(uint256).max);
        }
    }

    function _takeYVaultProfit() internal {
        uint256 _debt = balanceOfDebt();
        uint256 _valueInVault = _valueOfInvestment();
        if (_debt >= _valueInVault) {
            return;
        }

        uint256 profit = _valueInVault.sub(_debt);
        uint256 ySharesToWithdraw = _investmentTokenToYShares(profit);
        if (ySharesToWithdraw > 0) {
            yVault.withdraw(ySharesToWithdraw, address(this), maxLoss);
            _sellAForB(
                balanceOfInvestmentToken(),
                address(investmentToken),
                address(want)
            );
        }
    }

    function _depositToMakerVault(uint256 amount) internal {
        if (amount == 0) {
            return;
        }

        _checkAllowance(address(gemJoinAdapter), address(want), amount);

        uint256 price = _getWantTokenPrice();
        uint256 daiToMint =
            amount.mul(price).mul(MAX_BPS).div(collateralizationRatio).div(WAD);

        _lockCollateralAndMintDai(amount, daiToMint);
    }

    // Returns maximum collateral to withdraw while maintaining the target collateralization ratio
    function _maxWithdrawal() internal view returns (uint256) {
        // Denominated in want
        uint256 totalCollateral = balanceOfMakerVault();

        // Denominated in investment token
        uint256 totalDebt = balanceOfDebt();

        // If there is no debt to repay we can withdraw all the locked collateral
        if (totalDebt == 0) {
            return totalCollateral;
        }

        uint256 price = _getWantTokenPrice();

        // Min collateral in want that needs to be locked with the outstanding debt
        // Allow going to the lower rebalancing band
        uint256 minCollateral =
            collateralizationRatio
                .sub(rebalanceTolerance)
                .mul(totalDebt)
                .mul(WAD)
                .div(price)
                .div(MAX_BPS);

        // If we are under collateralized then it is not safe for us to withdraw anything
        if (minCollateral > totalCollateral) {
            return 0;
        }

        return totalCollateral.sub(minCollateral);
    }

    // ----------------- INTERNAL CALCS -----------------

    function balanceOfWant() internal view returns (uint256) {
        return want.balanceOf(address(this));
    }

    function balanceOfInvestmentToken() internal view returns (uint256) {
        return investmentToken.balanceOf(address(this));
    }

    function balanceOfDebt() internal view returns (uint256) {
        address urn = cdpManager.urns(cdpId);

        // Normalized outstanding stablecoin debt [wad]
        (, uint256 art) = vat.urns(ilk, urn);

        // Gets actual rate from the vat [ray]
        (, uint256 rate, , , ) = vat.ilks(ilk);

        // Return the present value of the debt with accrued fees
        return art.mul(rate).div(RAY);
    }

    // Returns collateral balance in the vault
    function balanceOfMakerVault() internal view returns (uint256) {
        address urn = cdpManager.urns(cdpId);
        (uint256 ink, ) = vat.urns(ilk, urn);
        return ink;
    }

    function _getWantTokenPrice() internal view returns (uint256) {
        uint256 minPrice;

        // Assume we are white-listed in the OSM
        (uint256 current, bool isCurrentValid) = YFItoUSDOSMProxy.peek();
        (uint256 future, bool isFutureValid) = YFItoUSDOSMProxy.peep();
        if (isCurrentValid && isFutureValid) {
            minPrice = Math.min(future, current);
        }

        // Non-ETH pairs have 8 decimals, so we need to adjust it to 18
        uint256 chainLinkPrice =
            uint256(chainlinkYFItoUSDPriceFeed.latestAnswer()) * 1e10;

        // Return the worst price available
        return Math.min(minPrice, chainLinkPrice);
    }

    function getCurrentMakerVaultRatio() internal view returns (uint256) {
        // spot: collateral price with safety margin returned in [ray]
        (, , uint256 spot, , ) = vat.ilks(ilk);

        // Liquidation ratio for the given ilk returned in [ray]
        // https://github.com/makerdao/dss/blob/master/src/spot.sol#L45
        (, uint256 liquidationRatio) = spotter.ilks(ilk);

        // Use pessimistic price to determine the worst ratio possible
        uint256 price = spot.mul(liquidationRatio).div(RAY * 1e9); // convert ray*ray --> wad

        price = Math.min(price, _getWantTokenPrice());

        uint256 totalCollateralValue =
            balanceOfMakerVault().mul(price).div(WAD);
        uint256 totalDebt = balanceOfDebt();

        // If for some reason we do not have debt (e.g: deposits under dust)
        // make sure the operation does not revert
        if (totalDebt == 0) {
            totalDebt = 1;
        }

        uint256 ratio = totalCollateralValue.mul(MAX_BPS).div(totalDebt);
        return ratio;
    }

    function _valueOfInvestment() internal view returns (uint256) {
        return
            yVault.balanceOf(address(this)).mul(yVault.pricePerShare()).div(
                10**yVault.decimals()
            );
    }

    function _investmentTokenToYShares(uint256 amount)
        internal
        view
        returns (uint256)
    {
        return amount.mul(10**yVault.decimals()).div(yVault.pricePerShare());
    }

    // Wrapper around library function to improve readibility
    function _lockCollateralAndMintDai(
        uint256 collateralAmount,
        uint256 daiToMint
    ) internal {
        MakerDaiDelegateLib.lockGemAndDraw(
            cdpManager,
            jug,
            gemJoinAdapter,
            daiJoinAdapter,
            cdpId,
            collateralAmount,
            daiToMint,
            balanceOfDebt()
        );
    }

    function _freeCollateralAndRepayDai(
        uint256 collateralAmount,
        uint256 daiToRepay
    ) internal {
        MakerDaiDelegateLib.wipeAndFreeGem(
            cdpManager,
            gemJoinAdapter,
            daiJoinAdapter,
            cdpId,
            collateralAmount,
            daiToRepay
        );
    }

    // ----------------- TOKEN CONVERSIONS -----------------

    function _convertInvestmentTokenToWant(uint256 amount)
        internal
        view
        returns (uint256)
    {
        return amount.mul(WAD).div(_getWantTokenPrice());
    }

    function getTokenOutPath(address _token_in, address _token_out)
        internal
        pure
        returns (address[] memory _path)
    {
        bool is_weth =
            _token_in == address(WETH) || _token_out == address(WETH);
        _path = new address[](is_weth ? 2 : 3);
        _path[0] = _token_in;

        if (is_weth) {
            _path[1] = _token_out;
        } else {
            _path[1] = address(WETH);
            _path[2] = _token_out;
        }
    }

    function _sellAForB(
        uint256 _amount,
        address tokenA,
        address tokenB
    ) internal {
        if (_amount == 0 || tokenA == tokenB) {
            return;
        }

        _checkAllowance(address(router), tokenA, _amount);
        router.swapExactTokensForTokens(
            _amount,
            0,
            getTokenOutPath(tokenA, tokenB),
            address(this),
            now
        );
    }

    function _buyInvestmentTokenWithWant(uint256 _amount) internal {
        if (_amount == 0 || address(investmentToken) == address(want)) {
            return;
        }

        _checkAllowance(address(router), address(want), _amount);
        router.swapTokensForExactTokens(
            _amount,
            type(uint256).max,
            getTokenOutPath(address(want), address(investmentToken)),
            address(this),
            now
        );
    }
}
