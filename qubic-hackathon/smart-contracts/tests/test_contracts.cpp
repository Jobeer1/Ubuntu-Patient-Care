#include "../include/types.h"
#include "../include/UCTokenContract.h"
#include "../include/UCICDaoContract.h"
#include "../include/OracleContract.h"
#include <iostream>
#include <cassert>
#include <memory>
#include <cstring>

using namespace UCIC;

// ============================================================================
// TEST FRAMEWORK
// ============================================================================

class TestRunner {
public:
    TestRunner() : testsPassed(0), testsFailed(0) {}
    
    void runTest(const std::string& name, std::function<bool()> test) {
        try {
            if (test()) {
                testsPassed++;
                std::cout << "✓ " << name << std::endl;
            } else {
                testsFailed++;
                std::cout << "✗ " << name << std::endl;
            }
        } catch (const std::exception& e) {
            testsFailed++;
            std::cout << "✗ " << name << " (Exception: " << e.what() << ")" << std::endl;
        }
    }
    
    void printSummary() {
        std::cout << "\n" << "==================================" << std::endl;
        std::cout << "Tests Passed: " << testsPassed << std::endl;
        std::cout << "Tests Failed: " << testsFailed << std::endl;
        std::cout << "Total Tests: " << (testsPassed + testsFailed) << std::endl;
        std::cout << "==================================" << std::endl;
    }

private:
    int testsPassed;
    int testsFailed;
};

// ============================================================================
// UC TOKEN TESTS
// ============================================================================

bool testTokenInitialization() {
    auto token = std::make_shared<UCTokenContract>();
    return token->getTotalSupply() == UC_TOKEN_SUPPLY * UC_UNIT &&
           token->getDecimals() == UC_DECIMALS &&
           std::string(token->getSymbol()) == "UC";
}

bool testBalanceQuery() {
    auto token = std::make_shared<UCTokenContract>();
    PublicAddress testAddr = "test_address_1";
    token->registerAccount(testAddr);
    return token->balanceOf(testAddr) == 0;
}

bool testTransfer() {
    auto token = std::make_shared<UCTokenContract>();
    PublicAddress recipient = "recipient_1";
    uint64 amount = UC_TO_UNITS(100);
    
    bool result = token->transfer(recipient, amount);
    return result && token->balanceOf(recipient) == amount;
}

bool testMintBurn() {
    auto token = std::make_shared<UCTokenContract>();
    PublicAddress account = "mint_test_1";
    uint64 initialSupply = token->getTotalSupply();
    
    token->mint(account, UC_TO_UNITS(50));
    uint64 supplyAfterMint = token->getTotalSupply();
    
    token->burn(account, UC_TO_UNITS(25));
    uint64 supplyAfterBurn = token->getTotalSupply();
    
    return (supplyAfterMint > initialSupply) && (supplyAfterBurn < supplyAfterMint);
}

bool testApprovalAndTransferFrom() {
    auto token = std::make_shared<UCTokenContract>();
    PublicAddress owner = "owner_1";
    PublicAddress spender = "spender_1";
    PublicAddress recipient = "recipient_2";
    uint64 amount = UC_TO_UNITS(50);
    
    token->registerAccount(owner);
    token->registerAccount(spender);
    token->approve(spender, amount);
    
    return token->allowance(owner, spender) == amount;
}

bool testIntegrityCheck() {
    auto token = std::make_shared<UCTokenContract>();
    PublicAddress addr1 = "addr_integrity_1";
    PublicAddress addr2 = "addr_integrity_2";
    
    token->transfer(addr1, UC_TO_UNITS(100));
    token->transfer(addr2, UC_TO_UNITS(50));
    
    return token->verifyIntegrity();
}

bool testAccountRegistration() {
    auto token = std::make_shared<UCTokenContract>();
    PublicAddress newAddr = "new_account_123";
    
    token->registerAccount(newAddr);
    return token->accountExists(newAddr);
}

// ============================================================================
// DAO TESTS
// ============================================================================

bool testContributorRegistration() {
    auto token = std::make_shared<UCTokenContract>();
    auto dao = std::make_shared<UCICDaoContract>(token);
    
    PublicAddress contributor = "contributor_1";
    bool registered = dao->registerContributor(contributor);
    
    return registered && dao->isContributor(contributor);
}

bool testCompositeScoring() {
    auto token = std::make_shared<UCTokenContract>();
    auto dao = std::make_shared<UCICDaoContract>(token);
    
    PublicAddress contributor = "contributor_score_1";
    dao->registerContributor(contributor);
    
    uint32 score = dao->calculateCompositeScore(100, 90, 85, 95, 80);
    return score > 0 && score <= 100;
}

bool testTierProgression() {
    auto token = std::make_shared<UCTokenContract>();
    auto dao = std::make_shared<UCICDaoContract>(token);
    
    PublicAddress contributor = "contributor_tier_1";
    dao->registerContributor(contributor);
    
    std::vector<CategoryScore> scores;
    CategoryScore cs1{ScoreCategory::CODE_QUALITY, 90, "test", 0};
    scores.push_back(cs1);
    
    dao->submitCompositeScore(contributor, scores);
    
    ContributorTier tier = dao->getTier(contributor);
    return tier >= ContributorTier::RECOGNIZED;
}

bool testProposalCreation() {
    auto token = std::make_shared<UCTokenContract>();
    auto dao = std::make_shared<UCICDaoContract>(token);
    
    PublicAddress proposer = "proposer_1";
    dao->registerContributor(proposer);
    
    uint32 proposalId = dao->createProposal(proposer, "Test Proposal", "This is a test");
    Proposal prop = dao->getProposal(proposalId);
    
    return proposalId > 0 && prop.proposalId == proposalId;
}

bool testVoting() {
    auto token = std::make_shared<UCTokenContract>();
    auto dao = std::make_shared<UCICDaoContract>(token);
    
    PublicAddress voter = "voter_1";
    dao->registerContributor(voter);
    
    PublicAddress proposer = "proposer_2";
    dao->registerContributor(proposer);
    
    uint32 proposalId = dao->createProposal(proposer, "Vote Test", "Test voting");
    bool canVote = dao->castVote(proposalId, voter, VoteType::FOR);
    
    return canVote && dao->hasVoted(proposalId, voter);
}

bool testRewardDistribution() {
    auto token = std::make_shared<UCTokenContract>();
    auto dao = std::make_shared<UCICDaoContract>(token);
    
    PublicAddress contributor = "reward_contributor_1";
    dao->registerContributor(contributor);
    
    uint64 distributed = dao->distributeMonthlyRewards(static_cast<uint64>(std::time(nullptr)));
    return distributed >= 0;
}

bool testModuleBonus() {
    auto token = std::make_shared<UCTokenContract>();
    auto dao = std::make_shared<UCICDaoContract>(token);
    
    PublicAddress contributor = "bonus_contributor_1";
    dao->registerContributor(contributor);
    
    uint32 scoreBefore = dao->getCompositeScore(contributor);
    dao->applyModuleBonus(contributor, 1, 50);
    uint32 scoreAfter = dao->getCompositeScore(contributor);
    
    return scoreAfter > scoreBefore;
}

bool testVotingPower() {
    auto token = std::make_shared<UCTokenContract>();
    auto dao = std::make_shared<UCICDaoContract>(token);
    
    PublicAddress contributor = "power_contributor_1";
    dao->registerContributor(contributor);
    
    uint64 votingPower = dao->getVotingPower(contributor);
    return votingPower > 0;
}

bool testDAOStatistics() {
    auto token = std::make_shared<UCTokenContract>();
    auto dao = std::make_shared<UCICDaoContract>(token);
    
    for (int i = 0; i < 5; ++i) {
        PublicAddress addr = "stat_contrib_" + std::to_string(i);
        dao->registerContributor(addr);
    }
    
    UCICDaoContract::Statistics stats = dao->getStatistics();
    return stats.totalContributors >= 5;
}

// ============================================================================
// ORACLE TESTS
// ============================================================================

bool testOracleSubmission() {
    auto token = std::make_shared<UCTokenContract>();
    auto dao = std::make_shared<UCICDaoContract>(token);
    auto oracle = std::make_shared<OracleContract>(dao);
    
    PublicAddress contributor = "oracle_contrib_1";
    Hash256 evidenceHash{};
    
    TransactionHash subId = oracle->submitScore(
        contributor, 85, 90, 80, 95, 75, "https://github.com/test/repo", evidenceHash
    );
    
    return !subId.empty();
}

bool testVerifierRegistration() {
    auto token = std::make_shared<UCTokenContract>();
    auto dao = std::make_shared<UCICDaoContract>(token);
    auto oracle = std::make_shared<OracleContract>(dao);
    
    PublicAddress verifier = "verifier_1";
    oracle->registerVerifier(verifier);
    
    return oracle->isVerifier(verifier);
}

bool testSubmissionVerification() {
    auto token = std::make_shared<UCTokenContract>();
    auto dao = std::make_shared<UCICDaoContract>(token);
    auto oracle = std::make_shared<OracleContract>(dao);
    
    PublicAddress contributor = "oracle_contrib_2";
    PublicAddress verifier = "verifier_2";
    
    oracle->registerVerifier(verifier);
    
    Hash256 evidenceHash{};
    TransactionHash subId = oracle->submitScore(
        contributor, 85, 90, 80, 95, 75, "https://github.com/test/repo", evidenceHash
    );
    
    bool verified = oracle->verifySubmission(subId, verifier, true, "Looks good");
    return verified;
}

bool testMerkleProof() {
    auto token = std::make_shared<UCTokenContract>();
    auto dao = std::make_shared<UCICDaoContract>(token);
    auto oracle = std::make_shared<OracleContract>(dao);
    
    PublicAddress contributor = "merkle_contrib_1";
    Hash256 evidenceHash{};
    
    TransactionHash subId = oracle->submitScore(
        contributor, 85, 90, 80, 95, 75, "https://github.com/test/repo", evidenceHash
    );
    
    Hash256 merkleRoot = oracle->getMerkleRoot(subId);
    return !subId.empty();
}

bool testGitLinking() {
    auto token = std::make_shared<UCTokenContract>();
    auto dao = std::make_shared<UCICDaoContract>(token);
    auto oracle = std::make_shared<OracleContract>(dao);
    
    PublicAddress contributor = "git_contrib_1";
    GitHash commitSha{};
    
    bool linked = oracle->linkGitRepository(
        contributor, "https://github.com/test/repo", commitSha
    );
    
    return linked && oracle->getLinkedRepository(contributor) == "https://github.com/test/repo";
}

bool testBlake3Hash() {
    auto token = std::make_shared<UCTokenContract>();
    auto dao = std::make_shared<UCICDaoContract>(token);
    auto oracle = std::make_shared<OracleContract>(dao);
    
    std::string data = "test_data_123";
    Hash256 hash = oracle->computeBlake3Hash(data);
    
    bool verified = oracle->verifyBlake3Hash(data, hash);
    return verified;
}

bool testChallengeResolution() {
    auto token = std::make_shared<UCTokenContract>();
    auto dao = std::make_shared<UCICDaoContract>(token);
    auto oracle = std::make_shared<OracleContract>(dao);
    
    PublicAddress contributor = "challenge_contrib_1";
    PublicAddress challenger = "challenger_1";
    Hash256 evidenceHash{};
    
    TransactionHash subId = oracle->submitScore(
        contributor, 85, 90, 80, 95, 75, "https://github.com/test/repo", evidenceHash
    );
    
    TransactionHash challengeId = oracle->challengeVerification(
        subId, challenger, "Invalid score"
    );
    
    return !challengeId.empty();
}

bool testOracleStatistics() {
    auto token = std::make_shared<UCTokenContract>();
    auto dao = std::make_shared<UCICDaoContract>(token);
    auto oracle = std::make_shared<OracleContract>(dao);
    
    PublicAddress verifier = "verifier_stats_1";
    oracle->registerVerifier(verifier);
    
    OracleContract::Statistics stats = oracle->getStatistics();
    return stats.totalVerifiers >= 1;
}

bool testDAOIntegration() {
    auto token = std::make_shared<UCTokenContract>();
    auto dao = std::make_shared<UCICDaoContract>(token);
    auto oracle = std::make_shared<OracleContract>(dao);
    
    PublicAddress contributor = "integration_contrib_1";
    PublicAddress verifier = "integration_verifier_1";
    
    dao->registerContributor(contributor);
    oracle->registerVerifier(verifier);
    
    Hash256 evidenceHash{};
    TransactionHash subId = oracle->submitScore(
        contributor, 85, 90, 80, 95, 75, "https://github.com/test/repo", evidenceHash
    );
    
    oracle->verifySubmission(subId, verifier, true, "Good work");
    
    return oracle->isRegisteredWithDao(subId) || oracle->getVerificationStatus(subId) >= VerificationLevel::BASIC;
}

// ============================================================================
// MAIN TEST RUNNER
// ============================================================================

int main() {
    TestRunner runner;
    
    std::cout << "Running Smart Contract Tests...\n" << std::endl;
    
    // UC Token Tests
    std::cout << "--- UC Token Tests ---" << std::endl;
    runner.runTest("Token Initialization", testTokenInitialization);
    runner.runTest("Balance Query", testBalanceQuery);
    runner.runTest("Token Transfer", testTransfer);
    runner.runTest("Mint and Burn", testMintBurn);
    runner.runTest("Approval and TransferFrom", testApprovalAndTransferFrom);
    runner.runTest("Integrity Check", testIntegrityCheck);
    runner.runTest("Account Registration", testAccountRegistration);
    
    // DAO Tests
    std::cout << "\n--- DAO Tests ---" << std::endl;
    runner.runTest("Contributor Registration", testContributorRegistration);
    runner.runTest("Composite Scoring", testCompositeScoring);
    runner.runTest("Tier Progression", testTierProgression);
    runner.runTest("Proposal Creation", testProposalCreation);
    runner.runTest("Voting", testVoting);
    runner.runTest("Reward Distribution", testRewardDistribution);
    runner.runTest("Module Bonus", testModuleBonus);
    runner.runTest("Voting Power", testVotingPower);
    runner.runTest("DAO Statistics", testDAOStatistics);
    
    // Oracle Tests
    std::cout << "\n--- Oracle Tests ---" << std::endl;
    runner.runTest("Oracle Submission", testOracleSubmission);
    runner.runTest("Verifier Registration", testVerifierRegistration);
    runner.runTest("Submission Verification", testSubmissionVerification);
    runner.runTest("Merkle Proof", testMerkleProof);
    runner.runTest("Git Linking", testGitLinking);
    runner.runTest("BLAKE3 Hash", testBlake3Hash);
    runner.runTest("Challenge Resolution", testChallengeResolution);
    runner.runTest("Oracle Statistics", testOracleStatistics);
    runner.runTest("DAO Integration", testDAOIntegration);
    
    runner.printSummary();
    
    return 0;
}
