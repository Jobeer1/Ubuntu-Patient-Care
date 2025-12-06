#include "../include/UCICDaoContract.h"
#include <algorithm>
#include <ctime>
#include <numeric>

namespace UCIC {

UCICDaoContract::UCICDaoContract(std::shared_ptr<UCTokenContract> tokenContract)
    : tokenContract(tokenContract),
      nextProposalId(1),
      totalRewardsDistributed(0),
      lastRewardDistribution(0) {}

bool UCICDaoContract::registerContributor(const PublicAddress& address,
                                         const PublicAddress& referrer) {
    if (contributors.find(address) != contributors.end()) {
        return false;  // Already registered
    }
    
    Contributor contrib;
    contrib.address = address;
    contrib.tier = ContributorTier::RECOGNIZED;
    contrib.compositeScore = 0;
    contrib.pointsEarned = 0;
    contrib.rewardsReceived = 0;
    contrib.joinedAt = static_cast<uint64>(std::time(nullptr));
    contrib.lastRewardClaimAt = 0;
    
    contributors[address] = contrib;
    
    TransactionHash txHash = "register_" + address + "_" + std::to_string(std::time(nullptr));
    recordGovernanceAction("register_contributor", address, txHash);
    
    return true;
}

Contributor UCICDaoContract::getContributor(const PublicAddress& address) const {
    auto it = contributors.find(address);
    if (it != contributors.end()) {
        return it->second;
    }
    return Contributor();
}

bool UCICDaoContract::isContributor(const PublicAddress& address) const {
    return contributors.find(address) != contributors.end();
}

uint64 UCICDaoContract::getContributorCount() const {
    return contributors.size();
}

bool UCICDaoContract::submitCompositeScore(const PublicAddress& contributor,
                                          const std::vector<CategoryScore>& scores) {
    auto it = contributors.find(contributor);
    if (it == contributors.end()) {
        return false;
    }
    
    // Calculate new composite score
    uint32 newScore = 0;
    uint8 counts[5] = {0};
    uint8 values[5] = {0};
    
    for (const auto& score : scores) {
        int idx = static_cast<int>(score.category);
        if (idx >= 0 && idx < 5) {
            values[idx] = score.score;
            counts[idx]++;
        }
    }
    
    newScore = calculateCompositeScore(values[0], values[1], values[2], values[3], values[4]);
    it->second.compositeScore = newScore;
    it->second.pointsEarned += newScore;
    
    updateTier(contributor);
    
    TransactionHash txHash = "score_" + contributor + "_" + std::to_string(std::time(nullptr));
    it->second.auditTrail.push_back(txHash);
    
    return true;
}

uint32 UCICDaoContract::calculateCompositeScore(uint8 codeQuality, uint8 documentation,
                                               uint8 testing, uint8 innovation,
                                               uint8 community) const {
    return (codeQuality * ScoringWeights::CODE_QUALITY_WEIGHT +
            documentation * ScoringWeights::DOCUMENTATION_WEIGHT +
            testing * ScoringWeights::TESTING_WEIGHT +
            innovation * ScoringWeights::INNOVATION_WEIGHT +
            community * ScoringWeights::COMMUNITY_WEIGHT) / 100;
}

uint32 UCICDaoContract::getCompositeScore(const PublicAddress& address) const {
    auto it = contributors.find(address);
    if (it != contributors.end()) {
        return it->second.compositeScore;
    }
    return 0;
}

ContributorTier UCICDaoContract::getTier(const PublicAddress& address) const {
    auto it = contributors.find(address);
    if (it != contributors.end()) {
        return it->second.tier;
    }
    return ContributorTier::RECOGNIZED;
}

uint32 UCICDaoContract::getTierThreshold(ContributorTier tier) const {
    switch (tier) {
        case ContributorTier::RECOGNIZED: return 0;
        case ContributorTier::SILVER: return 100;
        case ContributorTier::GOLD: return 250;
        case ContributorTier::PLATINUM: return 500;
        case ContributorTier::FOUNDER: return 1000;
        default: return 0;
    }
}

std::vector<PublicAddress> UCICDaoContract::getContributorsInTier(ContributorTier tier) const {
    std::vector<PublicAddress> result;
    for (const auto& contrib : contributors) {
        if (contrib.second.tier == tier) {
            result.push_back(contrib.first);
        }
    }
    return result;
}

uint64 UCICDaoContract::distributeMonthlyRewards(Timestamp timestamp) {
    uint64 rewardedCount = 0;
    uint64 monthlyPool = UC_TO_UNITS(MONTHLY_REWARD_POOL);
    
    // Calculate rewards by tier
    std::map<ContributorTier, std::vector<PublicAddress>> tierGroups;
    for (const auto& contrib : contributors) {
        tierGroups[contrib.second.tier].push_back(contrib.first);
    }
    
    // Distribute rewards proportionally
    for (int tierIdx = static_cast<int>(ContributorTier::FOUNDER); tierIdx >= 0; --tierIdx) {
        ContributorTier tier = static_cast<ContributorTier>(tierIdx);
        auto it = tierGroups.find(tier);
        
        if (it == tierGroups.end() || it->second.empty()) {
            continue;
        }
        
        uint8 percentage = REWARD_DISTRIBUTION[tierIdx];
        uint64 tierReward = (monthlyPool * percentage) / 100;
        uint64 perContributorReward = tierReward / it->second.size();
        
        for (const auto& address : it->second) {
            if (tokenContract->distributeReward(address, perContributorReward)) {
                auto contrib_it = contributors.find(address);
                if (contrib_it != contributors.end()) {
                    contrib_it->second.rewardsReceived += perContributorReward;
                    contrib_it->second.lastRewardClaimAt = timestamp;
                    rewardedCount++;
                }
            }
        }
    }
    
    totalRewardsDistributed += monthlyPool;
    lastRewardDistribution = timestamp;
    
    TransactionHash txHash = "reward_dist_" + std::to_string(timestamp);
    recordGovernanceAction("distribute_monthly_rewards", "__DAO__", txHash);
    
    return rewardedCount;
}

uint64 UCICDaoContract::getPendingReward(const PublicAddress& address) const {
    auto it = contributors.find(address);
    if (it == contributors.end()) {
        return 0;
    }
    
    // Simplified: return based on tier
    ContributorTier tier = it->second.tier;
    uint8 percentage = REWARD_DISTRIBUTION[static_cast<uint8>(tier)];
    uint64 monthlyPool = UC_TO_UNITS(MONTHLY_REWARD_POOL);
    
    return (monthlyPool * percentage) / 100;
}

uint64 UCICDaoContract::claimRewards(const PublicAddress& contributor) {
    auto it = contributors.find(contributor);
    if (it == contributors.end()) {
        return 0;
    }
    
    uint64 pending = getPendingReward(contributor);
    if (pending > 0) {
        it->second.rewardsReceived += pending;
        it->second.lastRewardClaimAt = static_cast<uint64>(std::time(nullptr));
    }
    
    return pending;
}

uint64 UCICDaoContract::getTotalRewardsDistributed() const {
    return totalRewardsDistributed;
}

uint32 UCICDaoContract::createProposal(const PublicAddress& proposer,
                                      const std::string& title,
                                      const std::string& description) {
    if (!isContributor(proposer)) {
        return 0;
    }
    
    Proposal proposal;
    proposal.proposalId = nextProposalId++;
    proposal.proposer = proposer;
    proposal.title = title;
    proposal.description = description;
    proposal.status = ProposalStatus::PENDING;
    proposal.votesFor = 0;
    proposal.votesAgainst = 0;
    proposal.votesAbstain = 0;
    proposal.createdAt = static_cast<uint64>(std::time(nullptr));
    proposal.votingDeadline = proposal.createdAt + (PROPOSAL_VOTING_PERIOD_HOURS * 3600);
    proposal.executionTime = 0;
    
    proposals[proposal.proposalId] = proposal;
    
    TransactionHash txHash = "proposal_" + std::to_string(proposal.proposalId);
    recordGovernanceAction("create_proposal", proposer, txHash);
    
    return proposal.proposalId;
}

bool UCICDaoContract::castVote(uint32 proposalId, const PublicAddress& voter, VoteType voteType) {
    auto prop_it = proposals.find(proposalId);
    if (prop_it == proposals.end()) {
        return false;
    }
    
    if (!isContributor(voter)) {
        return false;
    }
    
    // Check if already voted
    if (votes.find({proposalId, voter}) != votes.end()) {
        return false;
    }
    
    uint64 votingPower = getVotingPower(voter);
    
    Vote vote;
    vote.proposalId = proposalId;
    vote.voter = voter;
    vote.voteType = voteType;
    vote.votingPower = votingPower;
    vote.votedAt = static_cast<uint64>(std::time(nullptr));
    
    votes[{proposalId, voter}] = vote;
    
    // Update proposal vote counts
    if (voteType == VoteType::FOR) {
        prop_it->second.votesFor += votingPower;
    } else if (voteType == VoteType::AGAINST) {
        prop_it->second.votesAgainst += votingPower;
    } else {
        prop_it->second.votesAbstain += votingPower;
    }
    
    return true;
}

bool UCICDaoContract::executeProposal(uint32 proposalId) {
    auto it = proposals.find(proposalId);
    if (it == proposals.end() || it->second.status != ProposalStatus::PASSED) {
        return false;
    }
    
    it->second.status = ProposalStatus::EXECUTED;
    it->second.executionTime = static_cast<uint64>(std::time(nullptr));
    
    TransactionHash txHash = "execute_" + std::to_string(proposalId);
    recordGovernanceAction("execute_proposal", it->second.proposer, txHash);
    
    return true;
}

Proposal UCICDaoContract::getProposal(uint32 proposalId) const {
    auto it = proposals.find(proposalId);
    if (it != proposals.end()) {
        return it->second;
    }
    return Proposal();
}

uint64 UCICDaoContract::getVotingPower(const PublicAddress& address) const {
    ContributorTier tier = getTier(address);
    return getTierVotingPower(tier);
}

bool UCICDaoContract::hasVoted(uint32 proposalId, const PublicAddress& voter) const {
    return votes.find({proposalId, voter}) != votes.end();
}

std::vector<uint32> UCICDaoContract::getActiveProposals() const {
    std::vector<uint32> result;
    auto now = static_cast<uint64>(std::time(nullptr));
    
    for (const auto& prop : proposals) {
        if (prop.second.status == ProposalStatus::ACTIVE ||
            prop.second.status == ProposalStatus::PENDING) {
            if (prop.second.votingDeadline > now) {
                result.push_back(prop.first);
            }
        }
    }
    
    return result;
}

bool UCICDaoContract::applyModuleBonus(const PublicAddress& contributor,
                                      uint32 moduleId, uint32 bonusPoints) {
    auto it = contributors.find(contributor);
    if (it == contributors.end()) {
        return false;
    }
    
    it->second.compositeScore += bonusPoints;
    it->second.pointsEarned += bonusPoints;
    
    updateTier(contributor);
    
    return true;
}

std::map<uint32, uint32> UCICDaoContract::getAvailableBonuses() const {
    std::map<uint32, uint32> bonuses;
    bonuses[1] = 50;   // Module 1: +50 points
    bonuses[2] = 75;   // Module 2: +75 points
    bonuses[3] = 100;  // Module 3: +100 points
    bonuses[4] = 50;   // Module 4: +50 points
    return bonuses;
}

std::vector<TransactionHash> UCICDaoContract::getAuditTrail(const PublicAddress& address) const {
    auto it = contributors.find(address);
    if (it != contributors.end()) {
        return it->second.auditTrail;
    }
    return std::vector<TransactionHash>();
}

void UCICDaoContract::recordGovernanceAction(const std::string& action,
                                           const PublicAddress& actor,
                                           const TransactionHash& txHash) {
    governanceLog.push_back(txHash);
}

bool UCICDaoContract::verifyIntegrity() const {
    for (const auto& contrib : contributors) {
        if (contrib.second.address != contrib.first) {
            return false;
        }
    }
    return true;
}

UCICDaoContract::Statistics UCICDaoContract::getStatistics() const {
    Statistics stats;
    stats.totalContributors = contributors.size();
    stats.totalVotingPower = 0;
    stats.totalRewardsDistributed = totalRewardsDistributed;
    stats.activeProposals = getActiveProposals().size();
    stats.executedProposals = 0;
    stats.lastRewardDistributionTime = lastRewardDistribution;
    
    for (const auto& contrib : contributors) {
        stats.totalVotingPower += getVotingPower(contrib.first);
        stats.contributorsByTier[contrib.second.tier]++;
    }
    
    for (const auto& prop : proposals) {
        if (prop.second.status == ProposalStatus::EXECUTED) {
            stats.executedProposals++;
        }
    }
    
    return stats;
}

std::vector<PublicAddress> UCICDaoContract::getTopContributors(uint64 limit) const {
    std::vector<std::pair<PublicAddress, uint32>> sorted;
    
    for (const auto& contrib : contributors) {
        sorted.push_back({contrib.first, contrib.second.compositeScore});
    }
    
    std::sort(sorted.begin(), sorted.end(),
        [](const auto& a, const auto& b) { return a.second > b.second; });
    
    std::vector<PublicAddress> result;
    for (size_t i = 0; i < limit && i < sorted.size(); ++i) {
        result.push_back(sorted[i].first);
    }
    
    return result;
}

std::map<ContributorTier, uint64> UCICDaoContract::getTierDistribution() const {
    std::map<ContributorTier, uint64> distribution;
    
    for (const auto& contrib : contributors) {
        distribution[contrib.second.tier]++;
    }
    
    return distribution;
}

void UCICDaoContract::updateTier(const PublicAddress& address) {
    auto it = contributors.find(address);
    if (it == contributors.end()) {
        return;
    }
    
    uint32 score = it->second.compositeScore;
    ContributorTier newTier = ContributorTier::RECOGNIZED;
    
    if (score >= getTierThreshold(ContributorTier::PLATINUM)) {
        newTier = ContributorTier::PLATINUM;
    } else if (score >= getTierThreshold(ContributorTier::GOLD)) {
        newTier = ContributorTier::GOLD;
    } else if (score >= getTierThreshold(ContributorTier::SILVER)) {
        newTier = ContributorTier::SILVER;
    } else {
        newTier = ContributorTier::RECOGNIZED;
    }
    
    it->second.tier = newTier;
}

bool UCICDaoContract::validateProposal(const Proposal& proposal) const {
    return !proposal.title.empty() && !proposal.description.empty();
}

uint64 UCICDaoContract::calculateRewardAmount(ContributorTier tier) const {
    uint8 percentage = REWARD_DISTRIBUTION[static_cast<uint8>(tier)];
    uint64 monthlyPool = UC_TO_UNITS(MONTHLY_REWARD_POOL);
    return (monthlyPool * percentage) / 100;
}

}  // namespace UCIC
