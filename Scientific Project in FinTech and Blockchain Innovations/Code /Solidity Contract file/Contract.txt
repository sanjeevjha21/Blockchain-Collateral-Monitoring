// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title CollateralMonitor
 * @dev Tracks the physical weight of pledged collateral and deterministically 
 * updates its risk state based on predefined health thresholds.
 */
contract CollateralMonitor {

    // Core collateral metrics
    uint256 public pledgedWeight; // The initial, expected baseline weight
    uint256 public currentWeight; // The latest weight reported by the oracle

    // Risk escalation levels
    enum State {
        ACTIVE,     // Safe (>= 75%)
        FLAGGED_L1, // Warning (< 75%)
        FLAGGED_L2, // High Risk (< 50%)
        FLAGGED_L3  // Critical (< 25%)
    }
  
    State public currentState;

    // Emitted whenever the oracle successfully updates the contract state
    event WeightReported(
        uint256 weight,
        uint256 ratioPercent,
        State state,
        bytes32 proofHash, // Cryptographic anchor to off-chain visual evidence
        uint256 timestamp
    );

    /**
     * @dev Initializes the contract with the starting collateral weight.
     * @param _pledgedWeight The baseline weight of the fully collateralized asset.
     */
    constructor(uint256 _pledgedWeight) {
        pledgedWeight = _pledgedWeight;
        currentState = State.ACTIVE;
    }

    /**
     * @dev Called by the hardware oracle to report a new weight measurement.
     * @param newWeight The latest physical weight reading.
     * @param proofHash SHA-256 hash of the off-chain JSON proof.
     */
    function reportWeight(uint256 newWeight, bytes32 proofHash) external {

        // Update the live tracking variable
        currentWeight = newWeight;

        // Calculate collateral health ratio as a clean integer percentage
        uint256 ratio = (newWeight * 100) / pledgedWeight;

        // Deterministically update the risk state based on LTV thresholds
        if (ratio < 25) {
            currentState = State.FLAGGED_L3;
        } else if (ratio < 50) {
            currentState = State.FLAGGED_L2;
        } else if (ratio < 75) {
            currentState = State.FLAGGED_L1;
        } else {
            currentState = State.ACTIVE;
        }

        // Broadcast the update to external listeners (e.g., the web dashboard)
        emit WeightReported(
            newWeight,
            ratio,
            currentState,
            proofHash,
            block.timestamp
        );
    }
}