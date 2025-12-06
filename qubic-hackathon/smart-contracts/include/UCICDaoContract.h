#pragma once

#include "types.h"
#include "UCTokenContract.h"
#include <map>
#include <vector>
#include <memory>

namespace UCIC {

/**
 * UCIC DAO Contract
 * 
 * Decentralized Autonomous Organization for managing healthcare contributions
 * Features:
 *  - 5-tier contributor recognition system
 *  - Composite scoring based on multiple evaluation criteria
 *  - Democratic voting with tier-based voting power
 *  - Monthly reward distribution
 *  - Governance proposals
 */
class UCICDaoContract {
public:
    // ========================================================================
    // CONSTRUCTOR & LIFECYCLE
    // ========================================================================
    
    UCICDaoContract(std::shared_ptr<UCTokenContract> tokenContract);
    ~UCICDaoContract() = default;
    
    // ========================================================================
    // CONTRIBUTOR REGISTRATION & MANAGEMENT
    // ========================================================================
    
    /**
     * Register a new contributor
     * @param address Contributor public address
     * @param referrer Address of referring member (optional)
     * @return Success status
     */
    bool registerContributor(const PublicAddress& address, 
                            const PublicAddress& referrer = "");
    
    /**
     * Get contributor information
     * @param address Contributor address
     * @return Contributor structure if exists, empty contributor otherwise
     */
    Contributor getContributor(const PublicAddress& address) const;
    
    /**
     * Check if contributor is registered
     * @param address Address to check
     * @return True if contributor exists
     */
    bool isContributor(const PublicAddress& address) const;
    
    /**
     * Get total number of contributors
     * @return Number of registered contributors
     */
    uint64 getContributorCount() const;
    
    // ========================================================================
    // SCORING & TIER SYSTEM
    // ========================================================================
    
    /**
     * Submit category scores for a contributor
     * Called by Oracle contract after verification
     * @param contributor Target contributor address
     * @param scores Vector of CategoryScore structures
     * @return Success status
     */
    bool submitCompositeScore(const PublicAddress& contributor,
                             const std::vector<CategoryScore>& scores);
    
    /**
     * Calculate composite score from individual categories
     * Formula: (Code*0.25 + Docs*0.20 + Testing*0.20 + Innovation*0.20 + Community*0.15)
     * @param codeQuality Code quality score (0-100)
     * @param documentation Documentation quality (0-100)
     * @param testing Test coverage and quality (0-100)
     * @param innovation Innovation and originality (0-100)
     * @param community Community impact (0-100)
     * @return Composite score (0-100)
     */
    uint32 calculateCompositeScore(uint8 codeQuality, uint8 documentation,
                                  uint8 testing, uint8 innovation, 
                                  uint8 community) const;
    
    /**
     * Get contributor's current composite score
     * @param address Contributor address
     * @return Current composite score
     */
    uint32 getCompositeScore(const PublicAddress& address) const;
    
    /**
     * Get contributor's current tier
     * @param address Contributor address
     * @return Current tier
     */
    ContributorTier getTier(const PublicAddress& address) const;
    
    /**
     * Get tier threshold (minimum points required)
     * @param tier Tier to check
     * @return Minimum points required for tier
     */
    uint32 getTierThreshold(ContributorTier tier) const;
    
    /**
     * Get contributors at specific tier
     * @param tier Tier to query
     * @return Vector of addresses in that tier
     */
    std::vector<PublicAddress> getContributorsInTier(ContributorTier tier) const;
    
    // ========================================================================
    // REWARD DISTRIBUTION
    // ========================================================================
    
    /**
     * Distribute monthly rewards
     * Called once per month to distribute rewards based on tier
     * @param timestamp Current timestamp for this reward cycle
     * @return Number of contributors rewarded
     */
    uint64 distributeMonthlyRewards(Timestamp timestamp);
    
    /**
     * Get pending reward for contributor
     * @param address Contributor address
     * @return Pending reward amount in smallest units
     */
    uint64 getPendingReward(const PublicAddress& address) const;
    
    /**
     * Claim available rewards
     * @param contributor Address claiming rewards
     * @return Amount of rewards claimed
     */
    uint64 claimRewards(const PublicAddress& contributor);
    
    /**
     * Get total rewards distributed this period
     * @return Total rewards in smallest units
     */
    uint64 getTotalRewardsDistributed() const;
    
    // ========================================================================
    // GOVERNANCE & VOTING
    // ========================================================================
    
    /**
     * Create new governance proposal
     * @param proposer Address proposing change
     * @param title Proposal title
     * @param description Detailed description
     * @return Proposal ID
     */
    uint32 createProposal(const PublicAddress& proposer,
                         const std::string& title,
                         const std::string& description);
    
    /**
     * Cast vote on a proposal
     * Voting power depends on contributor tier
     * @param proposalId Proposal to vote on
     * @param voter Address of voter
     * @param voteType FOR, AGAINST, or ABSTAIN
     * @return Success status
     */
    bool castVote(uint32 proposalId, const PublicAddress& voter, VoteType voteType);
    
    /**
     * Execute a passed proposal
     * Only callable after voting period expires and proposal passes
     * @param proposalId Proposal to execute
     * @return Success status
     */
    bool executeProposal(uint32 proposalId);
    
    /**
     * Get proposal information
     * @param proposalId Proposal ID
     * @return Proposal structure
     */
    Proposal getProposal(uint32 proposalId) const;
    
    /**
     * Get voting power of contributor
     * @param address Contributor address
     * @return Voting power based on tier
     */
    uint64 getVotingPower(const PublicAddress& address) const;
    
    /**
     * Check if contributor has voted on proposal
     * @param proposalId Proposal to check
     * @param voter Voter address
     * @return True if voted
     */
    bool hasVoted(uint32 proposalId, const PublicAddress& voter) const;
    
    /**
     * Get active proposals
     * @return Vector of active proposal IDs
     */
    std::vector<uint32> getActiveProposals() const;
    
    // ========================================================================
    // MODULE BONUSES
    // ========================================================================
    
    /**
     * Apply module bonus to contributor score
     * Bonuses for completing specific modules
     * @param contributor Address to apply bonus to
     * @param moduleId Completed module identifier
     * @param bonusPoints Points to add
     * @return Success status
     */
    bool applyModuleBonus(const PublicAddress& contributor,
                         uint32 moduleId, uint32 bonusPoints);
    
    /**
     * Get available module bonuses
     * @return Map of module IDs to bonus values
     */
    std::map<uint32, uint32> getAvailableBonuses() const;
    
    // ========================================================================
    // AUDIT & INTEGRITY
    // ========================================================================
    
    /**
     * Get contributor audit trail
     * All scoring updates and transactions
     * @param address Contributor address
     * @return Vector of transaction hashes
     */
    std::vector<TransactionHash> getAuditTrail(const PublicAddress& address) const;
    
    /**
     * Record governance action
     * @param action Description of action
     * @param actor Address initiating action
     * @param txHash Transaction hash for this action
     */
    void recordGovernanceAction(const std::string& action,
                               const PublicAddress& actor,
                               const TransactionHash& txHash);
    
    /**
     * Verify DAO integrity
     * Check all data consistency
     * @return True if state is consistent
     */
    bool verifyIntegrity() const;
    
    // ========================================================================
    // STATISTICS & REPORTING
    // ========================================================================
    
    /**
     * Get DAO statistics
     */
    struct Statistics {
        uint64 totalContributors;
        uint64 totalVotingPower;
        uint64 totalRewardsDistributed;
        uint64 activeProposals;
        uint64 executedProposals;
        std::map<ContributorTier, uint64> contributorsByTier;
        uint64 lastRewardDistributionTime;
    };
    
    /**
     * Get current DAO statistics
     * @return Statistics structure
     */
    Statistics getStatistics() const;
    
    /**
     * Get top contributors by score
     * @param limit Maximum number of results
     * @return Vector of contributor addresses sorted by score
     */
    std::vector<PublicAddress> getTopContributors(uint64 limit = 10) const;
    
    /**
     * Get tier distribution
     * @return Map of tier to contributor count
     */
    std::map<ContributorTier, uint64> getTierDistribution() const;

private:
    std::shared_ptr<UCTokenContract> tokenContract;
    
    // Core data structures
    std::map<PublicAddress, Contributor> contributors;
    std::map<uint32, Proposal> proposals;
    std::map<std::pair<uint32, PublicAddress>, Vote> votes;
    std::vector<TransactionHash> governanceLog;
    
    uint32 nextProposalId;
    uint64 totalRewardsDistributed;
    Timestamp lastRewardDistribution;
    
    // Helper methods
    void updateTier(const PublicAddress& address);
    bool validateProposal(const Proposal& proposal) const;
    uint64 calculateRewardAmount(ContributorTier tier) const;
};

}  // namespace UCIC

#endif  // UNCICDAOCONTRACT_H
