#include "../include/UCTokenContract.h"
#include <algorithm>
#include <numeric>
#include <ctime>

namespace UCIC {

UCTokenContract::UCTokenContract()
    : totalSupply(UC_TOKEN_SUPPLY * UC_UNIT),
      treasuryBalance(0),
      transactionCount(0),
      treasuryAddress("__TREASURY__") {
    
    // Initialize treasury account
    Account treasury(treasuryAddress);
    treasury.balance = totalSupply;
    treasury.createdAt = static_cast<uint64>(std::time(nullptr));
    accounts[treasuryAddress] = treasury;
    treasuryBalance = totalSupply;
}

const char* UCTokenContract::getName() const {
    return "UC Token";
}

const char* UCTokenContract::getSymbol() const {
    return "UC";
}

uint8 UCTokenContract::getDecimals() const {
    return UC_DECIMALS;
}

uint64 UCTokenContract::getTotalSupply() const {
    return totalSupply;
}

uint64 UCTokenContract::getTreasuryBalance() const {
    return treasuryBalance;
}

uint64 UCTokenContract::balanceOf(const PublicAddress& account) const {
    auto it = accounts.find(account);
    if (it != accounts.end()) {
        return it->second.balance;
    }
    return 0;
}

uint64 UCTokenContract::allowance(const PublicAddress& owner, 
                                  const PublicAddress& spender) const {
    auto it = allowances.find({owner, spender});
    if (it != allowances.end()) {
        return it->second;
    }
    return 0;
}

bool UCTokenContract::transfer(const PublicAddress& recipient, uint64 amount) {
    if (!validateAddress(recipient) || !validateAmount(amount)) {
        return false;
    }
    
    auto it = accounts.find(treasuryAddress);
    if (it == accounts.end() || it->second.balance < amount) {
        return false;
    }
    
    // Register recipient if not exists
    if (accounts.find(recipient) == accounts.end()) {
        Account newAccount(recipient);
        newAccount.createdAt = static_cast<uint64>(std::time(nullptr));
        accounts[recipient] = newAccount;
    }
    
    // Transfer
    accounts[treasuryAddress].balance -= amount;
    accounts[recipient].balance += amount;
    accounts[treasuryAddress].nonce++;
    
    // Record transaction
    TransactionHash txHash = "tx_" + std::to_string(transactionCount++);
    recordTransaction(treasuryAddress, recipient, amount, txHash);
    
    return true;
}

bool UCTokenContract::transferFrom(const PublicAddress& owner,
                                  const PublicAddress& recipient,
                                  uint64 amount) {
    if (!validateAddress(owner) || !validateAddress(recipient) || !validateAmount(amount)) {
        return false;
    }
    
    // Check allowance
    uint64 allowed = allowance(owner, recipient);
    if (allowed < amount) {
        return false;
    }
    
    // Check owner balance
    auto ownerIt = accounts.find(owner);
    if (ownerIt == accounts.end() || ownerIt->second.balance < amount) {
        return false;
    }
    
    // Register recipient if not exists
    if (accounts.find(recipient) == accounts.end()) {
        Account newAccount(recipient);
        newAccount.createdAt = static_cast<uint64>(std::time(nullptr));
        accounts[recipient] = newAccount;
    }
    
    // Transfer
    accounts[owner].balance -= amount;
    accounts[recipient].balance += amount;
    accounts[owner].nonce++;
    
    // Update allowance
    allowances[{owner, recipient}] -= amount;
    
    // Record transaction
    TransactionHash txHash = "tx_" + std::to_string(transactionCount++);
    recordTransaction(owner, recipient, amount, txHash);
    
    return true;
}

bool UCTokenContract::approve(const PublicAddress& spender, uint64 amount) {
    if (!validateAddress(spender) || !validateAmount(amount)) {
        return false;
    }
    
    allowances[{treasuryAddress, spender}] = amount;
    return true;
}

bool UCTokenContract::increaseAllowance(const PublicAddress& spender, uint64 addedValue) {
    if (!validateAddress(spender) || !validateAmount(addedValue)) {
        return false;
    }
    
    uint64 current = allowance(treasuryAddress, spender);
    allowances[{treasuryAddress, spender}] = current + addedValue;
    return true;
}

bool UCTokenContract::decreaseAllowance(const PublicAddress& spender, uint64 subtractedValue) {
    if (!validateAddress(spender) || !validateAmount(subtractedValue)) {
        return false;
    }
    
    uint64 current = allowance(treasuryAddress, spender);
    if (current < subtractedValue) {
        return false;
    }
    
    allowances[{treasuryAddress, spender}] = current - subtractedValue;
    return true;
}

bool UCTokenContract::mint(const PublicAddress& account, uint64 amount) {
    if (!validateAddress(account) || !validateAmount(amount)) {
        return false;
    }
    
    // Register account if not exists
    if (accounts.find(account) == accounts.end()) {
        Account newAccount(account);
        newAccount.createdAt = static_cast<uint64>(std::time(nullptr));
        accounts[account] = newAccount;
    }
    
    accounts[account].balance += amount;
    totalSupply += amount;
    
    TransactionHash txHash = "mint_" + std::to_string(transactionCount++);
    recordTransaction("__MINT__", account, amount, txHash);
    
    return true;
}

bool UCTokenContract::burn(const PublicAddress& account, uint64 amount) {
    if (!validateAddress(account) || !validateAmount(amount)) {
        return false;
    }
    
    auto it = accounts.find(account);
    if (it == accounts.end() || it->second.balance < amount) {
        return false;
    }
    
    accounts[account].balance -= amount;
    totalSupply -= amount;
    
    TransactionHash txHash = "burn_" + std::to_string(transactionCount++);
    recordTransaction(account, "__BURN__", amount, txHash);
    
    return true;
}

bool UCTokenContract::distributeReward(const PublicAddress& recipient, uint64 amount) {
    if (!validateAddress(recipient) || !validateAmount(amount) || amount > treasuryBalance) {
        return false;
    }
    
    // Register recipient if not exists
    if (accounts.find(recipient) == accounts.end()) {
        Account newAccount(recipient);
        newAccount.createdAt = static_cast<uint64>(std::time(nullptr));
        accounts[recipient] = newAccount;
    }
    
    accounts[treasuryAddress].balance -= amount;
    treasuryBalance -= amount;
    accounts[recipient].balance += amount;
    
    TransactionHash txHash = "reward_" + std::to_string(transactionCount++);
    recordTransaction(treasuryAddress, recipient, amount, txHash);
    
    return true;
}

bool UCTokenContract::treasuryWithdraw(const PublicAddress& recipient, uint64 amount) {
    if (!validateAddress(recipient) || !validateAmount(amount) || amount > treasuryBalance) {
        return false;
    }
    
    accounts[treasuryAddress].balance -= amount;
    treasuryBalance -= amount;
    
    if (accounts.find(recipient) == accounts.end()) {
        Account newAccount(recipient);
        newAccount.createdAt = static_cast<uint64>(std::time(nullptr));
        accounts[recipient] = newAccount;
    }
    
    accounts[recipient].balance += amount;
    
    TransactionHash txHash = "withdraw_" + std::to_string(transactionCount++);
    recordTransaction(treasuryAddress, recipient, amount, txHash);
    
    return true;
}

bool UCTokenContract::treasuryDeposit(const PublicAddress& contributor, uint64 amount) {
    if (!validateAddress(contributor) || !validateAmount(amount)) {
        return false;
    }
    
    auto it = accounts.find(contributor);
    if (it == accounts.end() || it->second.balance < amount) {
        return false;
    }
    
    accounts[contributor].balance -= amount;
    accounts[treasuryAddress].balance += amount;
    treasuryBalance += amount;
    
    TransactionHash txHash = "deposit_" + std::to_string(transactionCount++);
    recordTransaction(contributor, treasuryAddress, amount, txHash);
    
    return true;
}

bool UCTokenContract::registerAccount(const PublicAddress& account) {
    if (!validateAddress(account)) {
        return false;
    }
    
    if (accounts.find(account) != accounts.end()) {
        return false;  // Already registered
    }
    
    Account newAccount(account);
    newAccount.createdAt = static_cast<uint64>(std::time(nullptr));
    accounts[account] = newAccount;
    
    return true;
}

bool UCTokenContract::accountExists(const PublicAddress& account) const {
    return accounts.find(account) != accounts.end();
}

uint64 UCTokenContract::getAccountCount() const {
    return accounts.size();
}

std::vector<TransactionHash> UCTokenContract::getTransactionHistory(
    const PublicAddress& account) const {
    auto it = transactionHistories.find(account);
    if (it != transactionHistories.end()) {
        return it->second;
    }
    return std::vector<TransactionHash>();
}

void UCTokenContract::recordTransaction(const PublicAddress& from, 
                                       const PublicAddress& to,
                                       uint64 amount,
                                       const TransactionHash& txHash) {
    transactionHistories[from].push_back(txHash);
    transactionHistories[to].push_back(txHash);
}

UCTokenContract::State UCTokenContract::getContractState() const {
    State state;
    state.totalSupply = totalSupply;
    state.treasuryBalance = treasuryBalance;
    state.circulatingSupply = totalSupply - treasuryBalance;
    state.accountCount = accounts.size();
    state.totalTransactions = transactionCount;
    return state;
}

bool UCTokenContract::verifyIntegrity() const {
    uint64 sumBalances = 0;
    for (const auto& account : accounts) {
        sumBalances += account.second.balance;
    }
    return sumBalances == totalSupply;
}

bool UCTokenContract::validateAmount(uint64 amount) const {
    return amount > 0 && amount <= totalSupply;
}

bool UCTokenContract::validateAddress(const PublicAddress& addr) const {
    return !addr.empty() && addr.length() <= 256;
}

}  // namespace UCIC
