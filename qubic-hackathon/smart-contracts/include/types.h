#pragma once

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>
#include <array>
#include <memory>
#include <cstring>

// ============================================================================
// QUBIC BLOCKCHAIN TYPES & CONSTANTS
// ============================================================================

namespace UCIC {

// Basic Types
using uint64 = std::uint64_t;
using uint32 = std::uint32_t;
using uint16 = std::uint16_t;
using uint8 = std::uint8_t;
using int64 = std::int64_t;
using int32 = std::int32_t;

using PublicAddress = std::string;
using TransactionHash = std::string;
using Timestamp = uint64;

// ============================================================================
// TOKEN CONSTANTS
// ============================================================================

constexpr uint64 UC_TOKEN_SUPPLY = 1000;  // 1,000 UC total supply
constexpr uint8 UC_DECIMALS = 8;          // 8 decimal places
constexpr uint64 UC_UNIT = 100000000ULL;  // 1 UC = 10^8 smallest units

// Token values in smallest units
constexpr uint64 UC_TO_UNITS(uint64 uc) { return uc * UC_UNIT; }

// ============================================================================
// DAO CONSTANTS
// ============================================================================

// Tier System
enum class ContributorTier : uint8 {
    RECOGNIZED = 0,      // Newly recognized contributor
    SILVER = 1,          // 100+ points
    GOLD = 2,            // 250+ points
    PLATINUM = 3,        // 500+ points
    FOUNDER = 4          // Reserved for DAO founders
};

// Voting Power Multipliers
constexpr uint8 VOTING_POWER[5] = {
    1,  // RECOGNIZED: 1x
    2,  // SILVER: 2x
    3,  // GOLD: 3x
    4,  // PLATINUM: 4x
    5   // FOUNDER: 5x
};

// Monthly Rewards (in UC)
constexpr uint64 MONTHLY_REWARD_POOL = 30;  // 30 UC per month total
// Distribution: 50% to top tier, 30% to second, 20% to third and below
constexpr uint8 REWARD_DISTRIBUTION[5] = {
    20,  // RECOGNIZED: 20% (0.2 UC)
    20,  // SILVER: 20% (0.2 UC)
    30,  // GOLD: 30% (0.3 UC)
    40,  // PLATINUM: 40% (0.4 UC)
    100  // FOUNDER: Special distribution
};

// ============================================================================
// ORACLE CONSTANTS
// ============================================================================

// Verification Levels
enum class VerificationLevel : uint8 {
    UNVERIFIED = 0,
    BASIC = 1,
    ADVANCED = 2,
    AUDIT_COMPLETE = 3
};

// Score Categories
enum class ScoreCategory : uint8 {
    CODE_QUALITY = 0,
    DOCUMENTATION = 1,
    TESTING = 2,
    INNOVATION = 3,
    COMMUNITY_IMPACT = 4
};

constexpr uint8 NUM_SCORE_CATEGORIES = 5;
constexpr uint8 MAX_CATEGORY_SCORE = 100;

// BLAKE3 Hash Size (32 bytes)
using Hash256 = std::array<uint8, 32>;

// Git SHA-1 Hash (40 hex chars = 20 bytes)
using GitHash = std::array<uint8, 20>;

// ============================================================================
// GOVERNANCE CONSTANTS
// ============================================================================

constexpr uint64 PROPOSAL_VOTING_PERIOD_HOURS = 72;
constexpr uint64 PROPOSAL_EXECUTION_DELAY_HOURS = 24;
constexpr uint8 MIN_VOTING_THRESHOLD_PERCENT = 50;

enum class ProposalStatus : uint8 {
    PENDING = 0,
    ACTIVE = 1,
    PASSED = 2,
    FAILED = 3,
    EXECUTED = 4,
    CANCELLED = 5
};

enum class VoteType : uint8 {
    FOR = 0,
    AGAINST = 1,
    ABSTAIN = 2
};

// ============================================================================
// TREASURY CONSTANTS
// ============================================================================

// Treasury Reserve: 470 UC (47% of supply) kept for governance stability
constexpr uint64 TREASURY_RESERVE = 470;

// Allocation percentages for distributed UC
constexpr uint8 ALLOCATION_REWARDS = 30;    // 3% of supply for monthly rewards
constexpr uint8 ALLOCATION_INCENTIVES = 50; // 5% of supply for incentives
constexpr uint8 ALLOCATION_OPERATIONS = 20; // 2% of supply for operational costs

// ============================================================================
// COMPOSITE SCORING FORMULA
// ============================================================================

struct ScoringWeights {
    static constexpr uint8 CODE_QUALITY_WEIGHT = 25;
    static constexpr uint8 DOCUMENTATION_WEIGHT = 20;
    static constexpr uint8 TESTING_WEIGHT = 20;
    static constexpr uint8 INNOVATION_WEIGHT = 20;
    static constexpr uint8 COMMUNITY_WEIGHT = 15;
    static constexpr uint8 TOTAL_WEIGHT = 100;
};

// Composite Score = (CodeQuality * 0.25) + (Docs * 0.20) + (Testing * 0.20) 
//                 + (Innovation * 0.20) + (Community * 0.15)

// ============================================================================
// DATA STRUCTURES
// ============================================================================

struct Account {
    PublicAddress address;
    uint64 balance;
    uint64 nonce;
    Timestamp createdAt;
    
    Account() : balance(0), nonce(0), createdAt(0) {}
    Account(const PublicAddress& addr) 
        : address(addr), balance(0), nonce(0), createdAt(0) {}
};

struct Contributor {
    PublicAddress address;
    ContributorTier tier;
    uint32 compositeScore;
    uint64 pointsEarned;
    uint64 rewardsReceived;
    Timestamp joinedAt;
    Timestamp lastRewardClaimAt;
    std::vector<TransactionHash> auditTrail;
    
    Contributor() 
        : tier(ContributorTier::RECOGNIZED), compositeScore(0), 
          pointsEarned(0), rewardsReceived(0), joinedAt(0), lastRewardClaimAt(0) {}
};

struct CategoryScore {
    ScoreCategory category;
    uint8 score;
    std::string evidence;
    Timestamp submittedAt;
    
    CategoryScore() : category(ScoreCategory::CODE_QUALITY), score(0), submittedAt(0) {}
};

struct OracleSubmission {
    PublicAddress submitter;
    PublicAddress targetContributor;
    std::vector<CategoryScore> scores;
    GitHash gitSHA1;
    Hash256 dataHash;
    VerificationLevel verificationLevel;
    uint8 verifierCount;
    Timestamp submittedAt;
    std::vector<TransactionHash> verificationChain;
    
    OracleSubmission() 
        : verificationLevel(VerificationLevel::UNVERIFIED), verifierCount(0), submittedAt(0) {}
};

struct Proposal {
    uint32 proposalId;
    PublicAddress proposer;
    std::string title;
    std::string description;
    ProposalStatus status;
    uint64 votesFor;
    uint64 votesAgainst;
    uint64 votesAbstain;
    Timestamp createdAt;
    Timestamp votingDeadline;
    Timestamp executionTime;
    
    Proposal() 
        : proposalId(0), status(ProposalStatus::PENDING), 
          votesFor(0), votesAgainst(0), votesAbstain(0),
          createdAt(0), votingDeadline(0), executionTime(0) {}
};

struct Vote {
    uint32 proposalId;
    PublicAddress voter;
    VoteType voteType;
    uint64 votingPower;
    Timestamp votedAt;
    
    Vote() 
        : proposalId(0), voteType(VoteType::ABSTAIN), votingPower(0), votedAt(0) {}
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

inline bool isValidAddress(const PublicAddress& addr) {
    return !addr.empty() && addr.length() <= 256;
}

inline uint8 getTierVotingPower(ContributorTier tier) {
    return VOTING_POWER[static_cast<uint8>(tier)];
}

inline uint64 calculateReward(ContributorTier tier, uint64 baseAmount) {
    uint8 percentage = REWARD_DISTRIBUTION[static_cast<uint8>(tier)];
    return (baseAmount * percentage) / 100;
}

inline bool isValidScore(uint8 score) {
    return score >= 0 && score <= MAX_CATEGORY_SCORE;
}

inline uint32 calculateCompositeScore(
    uint8 codeQuality, uint8 documentation, uint8 testing, 
    uint8 innovation, uint8 community) {
    return (codeQuality * ScoringWeights::CODE_QUALITY_WEIGHT +
            documentation * ScoringWeights::DOCUMENTATION_WEIGHT +
            testing * ScoringWeights::TESTING_WEIGHT +
            innovation * ScoringWeights::INNOVATION_WEIGHT +
            community * ScoringWeights::COMMUNITY_WEIGHT) / 100;
}

}  // namespace UCIC

#endif  // TYPES_H
