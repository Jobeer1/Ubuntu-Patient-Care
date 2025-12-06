#pragma once

#include "types.h"
#include <map>
#include <set>

namespace UCIC {

/**
 * UC Token Contract
 * 
 * Implements an ERC20-equivalent token for the Qubic blockchain.
 * Total supply: 1,000 UC (with 8 decimal places)
 * Features:
 *  - Transfer functionality with balance tracking
 *  - Mint/Burn for governance
 *  - Treasury management
 *  - Access control for sensitive operations
 */
class UCTokenContract {
public:
    // ========================================================================
    // CONSTRUCTOR & LIFECYCLE
    // ========================================================================
    
    UCTokenContract();
    ~UCTokenContract() = default;
    
    // ========================================================================
    // TOKEN INFORMATION
    // ========================================================================
    
    /**
     * Get token name
     */
    const char* getName() const;
    
    /**
     * Get token symbol
     */
    const char* getSymbol() const;
    
    /**
     * Get number of decimal places
     */
    uint8 getDecimals() const;
    
    /**
     * Get total token supply
     */
    uint64 getTotalSupply() const;
    
    /**
     * Get treasury balance
     */
    uint64 getTreasuryBalance() const;
    
    // ========================================================================
    // BALANCE QUERIES
    // ========================================================================
    
    /**
     * Get balance of an account
     * @param account Address of account to check
     * @return Balance in smallest units (1 UC = 10^8 units)
     */
    uint64 balanceOf(const PublicAddress& account) const;
    
    /**
     * Get approved allowance from owner to spender
     * @param owner Token owner address
     * @param spender Approved spender address
     * @return Approved amount in smallest units
     */
    uint64 allowance(const PublicAddress& owner, const PublicAddress& spender) const;
    
    // ========================================================================
    // TRANSFER OPERATIONS
    // ========================================================================
    
    /**
     * Transfer tokens from sender to recipient
     * @param recipient Target address
     * @param amount Amount in smallest units
     * @return Success status
     */
    bool transfer(const PublicAddress& recipient, uint64 amount);
    
    /**
     * Transfer tokens on behalf of owner (requires approval)
     * @param owner Token owner address
     * @param recipient Target address
     * @param amount Amount in smallest units
     * @return Success status
     */
    bool transferFrom(const PublicAddress& owner, const PublicAddress& recipient, uint64 amount);
    
    /**
     * Approve spender to use tokens on behalf of sender
     * @param spender Address to approve
     * @param amount Amount to approve in smallest units
     * @return Success status
     */
    bool approve(const PublicAddress& spender, uint64 amount);
    
    /**
     * Increase approved allowance
     * @param spender Address to increase allowance for
     * @param addedValue Amount to add to allowance
     * @return Success status
     */
    bool increaseAllowance(const PublicAddress& spender, uint64 addedValue);
    
    /**
     * Decrease approved allowance
     * @param spender Address to decrease allowance for
     * @param subtractedValue Amount to subtract from allowance
     * @return Success status
     */
    bool decreaseAllowance(const PublicAddress& spender, uint64 subtractedValue);
    
    // ========================================================================
    // MINTING & BURNING (GOVERNANCE ONLY)
    // ========================================================================
    
    /**
     * Mint new tokens to an account
     * Only callable by DAO governance
     * @param account Target account for minted tokens
     * @param amount Amount to mint in smallest units
     * @return Success status
     */
    bool mint(const PublicAddress& account, uint64 amount);
    
    /**
     * Burn tokens from an account
     * Reduces total supply, only for governance operations
     * @param account Account to burn from
     * @param amount Amount to burn in smallest units
     * @return Success status
     */
    bool burn(const PublicAddress& account, uint64 amount);
    
    // ========================================================================
    // TREASURY MANAGEMENT
    // ========================================================================
    
    /**
     * Distribute reward tokens from treasury
     * Used by DAO for monthly rewards
     * @param recipient Address to receive reward
     * @param amount Amount in smallest units
     * @return Success status
     */
    bool distributeReward(const PublicAddress& recipient, uint64 amount);
    
    /**
     * Withdraw from treasury (for operational costs)
     * Only callable by governance
     * @param recipient Address to receive funds
     * @param amount Amount to withdraw
     * @return Success status
     */
    bool treasuryWithdraw(const PublicAddress& recipient, uint64 amount);
    
    /**
     * Return funds to treasury
     * @param contributor Address contributing funds back
     * @param amount Amount to return
     * @return Success status
     */
    bool treasuryDeposit(const PublicAddress& contributor, uint64 amount);
    
    // ========================================================================
    // ACCOUNT MANAGEMENT
    // ========================================================================
    
    /**
     * Register a new account on the contract
     * @param account Address to register
     * @return Success status
     */
    bool registerAccount(const PublicAddress& account);
    
    /**
     * Check if account exists
     * @param account Address to check
     * @return True if account is registered
     */
    bool accountExists(const PublicAddress& account) const;
    
    /**
     * Get number of registered accounts
     * @return Total account count
     */
    uint64 getAccountCount() const;
    
    // ========================================================================
    // TRANSACTION HISTORY
    // ========================================================================
    
    /**
     * Get transaction history for an account
     * @param account Address to query
     * @return Vector of transaction hashes
     */
    std::vector<TransactionHash> getTransactionHistory(const PublicAddress& account) const;
    
    /**
     * Record transaction in audit log
     * @param from Sender address
     * @param to Recipient address
     * @param amount Amount transferred
     * @param txHash Transaction hash
     */
    void recordTransaction(const PublicAddress& from, const PublicAddress& to, 
                          uint64 amount, const TransactionHash& txHash);
    
    // ========================================================================
    // STATE QUERIES
    // ========================================================================
    
    /**
     * Get contract state summary
     */
    struct State {
        uint64 totalSupply;
        uint64 treasuryBalance;
        uint64 circulatingSupply;
        uint64 accountCount;
        uint64 totalTransactions;
    };
    
    /**
     * Get current contract state
     * @return State structure with all key metrics
     */
    State getContractState() const;
    
    /**
     * Verify contract integrity
     * Ensures balances sum correctly
     * @return True if state is consistent
     */
    bool verifyIntegrity() const;

private:
    // Core data structures
    std::map<PublicAddress, Account> accounts;
    std::map<std::pair<PublicAddress, PublicAddress>, uint64> allowances;
    std::map<PublicAddress, std::vector<TransactionHash>> transactionHistories;
    
    uint64 totalSupply;
    uint64 treasuryBalance;
    uint64 transactionCount;
    
    // Access control
    std::set<PublicAddress> governors;
    PublicAddress treasuryAddress;
    
    // Helper methods
    bool validateAmount(uint64 amount) const;
    bool validateAddress(const PublicAddress& addr) const;
    void updateBalance(const PublicAddress& account, int64 delta);
};

}  // namespace UCIC

#endif  // UCTOKENCONTRACT_H
