#include "../include/OracleContract.h"
#include <algorithm>
#include <ctime>
#include <sstream>
#include <iomanip>

namespace UCIC {

OracleContract::OracleContract(std::shared_ptr<UCICDaoContract> daoContract)
    : daoContract(daoContract),
      totalVerifications(0),
      acceptedVerifications(0) {}

TransactionHash OracleContract::submitScore(const PublicAddress& contributor,
                                           uint8 codeQuality,
                                           uint8 documentation,
                                           uint8 testing,
                                           uint8 innovation,
                                           uint8 community,
                                           const std::string& gitRepository,
                                           const Hash256& evidenceHash) {
    
    if (!validateScores(codeQuality, documentation, testing, innovation, community)) {
        return "";
    }
    
    OracleSubmission submission;
    submission.submitter = contributor;
    submission.targetContributor = contributor;
    submission.gitSHA1 = {};
    submission.dataHash = evidenceHash;
    submission.verificationLevel = VerificationLevel::UNVERIFIED;
    submission.verifierCount = 0;
    submission.submittedAt = static_cast<uint64>(std::time(nullptr));
    
    // Add category scores
    CategoryScore score1{ScoreCategory::CODE_QUALITY, codeQuality, "Code Quality Review", submission.submittedAt};
    CategoryScore score2{ScoreCategory::DOCUMENTATION, documentation, "Documentation Review", submission.submittedAt};
    CategoryScore score3{ScoreCategory::TESTING, testing, "Testing Coverage", submission.submittedAt};
    CategoryScore score4{ScoreCategory::INNOVATION, innovation, "Innovation Assessment", submission.submittedAt};
    CategoryScore score5{ScoreCategory::COMMUNITY_IMPACT, community, "Community Impact", submission.submittedAt};
    
    submission.scores.push_back(score1);
    submission.scores.push_back(score2);
    submission.scores.push_back(score3);
    submission.scores.push_back(score4);
    submission.scores.push_back(score5);
    
    TransactionHash submissionId = "sub_" + contributor + "_" + std::to_string(submission.submittedAt);
    submissions[submissionId] = submission;
    
    // Create Merkle proof
    Hash256 merkleRoot = createMerkleProof(submissionId);
    merkleRoots[submissionId] = merkleRoot;
    
    // Store Git repository
    if (!gitRepository.empty()) {
        gitRepositories[contributor] = gitRepository;
    }
    
    recordAction("submit_score", contributor, submissionId);
    
    return submissionId;
}

bool OracleContract::verifySubmission(const TransactionHash& submissionId,
                                    const PublicAddress& verifier,
                                    bool approved,
                                    const std::string& notes) {
    
    auto it = submissions.find(submissionId);
    if (it == submissions.end() || !isVerifier(verifier)) {
        return false;
    }
    
    OracleSubmission& submission = it->second;
    
    // Record verification
    VerificationRecord record;
    record.verifier = verifier;
    record.approved = approved;
    record.notes = notes;
    record.verifiedAt = static_cast<uint64>(std::time(nullptr));
    
    verificationChains[submissionId].push_back(record);
    submission.verifierCount++;
    
    if (approved) {
        acceptedVerifications++;
    }
    
    totalVerifications++;
    
    // Update verification level based on verifier count
    if (submission.verifierCount >= 3) {
        submission.verificationLevel = approved ? 
            VerificationLevel::AUDIT_COMPLETE : VerificationLevel::BASIC;
    } else if (submission.verifierCount >= 1) {
        submission.verificationLevel = approved ? 
            VerificationLevel::ADVANCED : VerificationLevel::BASIC;
    }
    
    recordAction("verify_submission", verifier, submissionId);
    
    return true;
}

OracleSubmission OracleContract::getSubmission(const TransactionHash& submissionId) const {
    auto it = submissions.find(submissionId);
    if (it != submissions.end()) {
        return it->second;
    }
    return OracleSubmission();
}

std::vector<TransactionHash> OracleContract::getSubmissionsForContributor(
    const PublicAddress& contributor) const {
    
    std::vector<TransactionHash> result;
    for (const auto& sub : submissions) {
        if (sub.second.targetContributor == contributor) {
            result.push_back(sub.first);
        }
    }
    return result;
}

VerificationLevel OracleContract::getVerificationStatus(const TransactionHash& submissionId) const {
    auto it = submissions.find(submissionId);
    if (it != submissions.end()) {
        return it->second.verificationLevel;
    }
    return VerificationLevel::UNVERIFIED;
}

bool OracleContract::linkGitRepository(const PublicAddress& contributor,
                                      const std::string& repoUrl,
                                      const GitHash& commitSha) {
    
    gitRepositories[contributor] = repoUrl;
    return true;
}

std::string OracleContract::getLinkedRepository(const PublicAddress& contributor) const {
    auto it = gitRepositories.find(contributor);
    if (it != gitRepositories.end()) {
        return it->second;
    }
    return "";
}

bool OracleContract::verifyGitCommit(const std::string& repoUrl, const GitHash& commitSha) const {
    // In real implementation, would query Git service
    // For this implementation, we accept any valid repository URL
    return !repoUrl.empty();
}

Hash256 OracleContract::createMerkleProof(const TransactionHash& submissionId) {
    auto it = submissions.find(submissionId);
    if (it == submissions.end()) {
        return Hash256{};
    }
    
    return computeMerkleTree(it->second);
}

bool OracleContract::verifyMerkleProof(const TransactionHash& submissionId,
                                     const Hash256& merkleRoot) const {
    auto it = merkleRoots.find(submissionId);
    if (it != merkleRoots.end()) {
        for (size_t i = 0; i < 32; ++i) {
            if (it->second[i] != merkleRoot[i]) {
                return false;
            }
        }
        return true;
    }
    return false;
}

Hash256 OracleContract::getMerkleRoot(const TransactionHash& submissionId) const {
    auto it = merkleRoots.find(submissionId);
    if (it != merkleRoots.end()) {
        return it->second;
    }
    return Hash256{};
}

Hash256 OracleContract::computeBlake3Hash(const std::string& data) const {
    Hash256 result{};
    // Simplified: XOR hash function for demonstration
    size_t pos = 0;
    for (size_t i = 0; i < 32 && pos < data.length(); ++i) {
        result[i] = static_cast<uint8>(data[pos++]) ^ static_cast<uint8>(data[pos % data.length()]);
    }
    return result;
}

bool OracleContract::verifyBlake3Hash(const std::string& data,
                                    const Hash256& expectedHash) const {
    Hash256 computed = computeBlake3Hash(data);
    for (size_t i = 0; i < 32; ++i) {
        if (computed[i] != expectedHash[i]) {
            return false;
        }
    }
    return true;
}

std::vector<OracleContract::VerificationRecord> OracleContract::getVerificationChain(
    const TransactionHash& submissionId) const {
    
    auto it = verificationChains.find(submissionId);
    if (it != verificationChains.end()) {
        return it->second;
    }
    return std::vector<VerificationRecord>();
}

TransactionHash OracleContract::recordAction(const std::string& action,
                                            const PublicAddress& actor,
                                            const TransactionHash& submissionId) {
    TransactionHash actionHash = action + "_" + actor + "_" + std::to_string(std::time(nullptr));
    auditLog.push_back(actionHash);
    return actionHash;
}

bool OracleContract::registerVerifier(const PublicAddress& address) {
    if (verifiers.find(address) != verifiers.end()) {
        return false;
    }
    
    verifiers.insert(address);
    return true;
}

bool OracleContract::isVerifier(const PublicAddress& address) const {
    return verifiers.find(address) != verifiers.end();
}

std::vector<PublicAddress> OracleContract::getVerifiers() const {
    return std::vector<PublicAddress>(verifiers.begin(), verifiers.end());
}

uint64 OracleContract::getVerifierStats(const PublicAddress& verifier) const {
    uint64 count = 0;
    for (const auto& chain : verificationChains) {
        for (const auto& record : chain.second) {
            if (record.verifier == verifier) {
                count++;
            }
        }
    }
    return count;
}

bool OracleContract::removeVerifier(const PublicAddress& address) {
    if (verifiers.find(address) != verifiers.end()) {
        verifiers.erase(address);
        return true;
    }
    return false;
}

TransactionHash OracleContract::challengeVerification(const TransactionHash& submissionId,
                                                    const PublicAddress& challenger,
                                                    const std::string& reason) {
    auto it = submissions.find(submissionId);
    if (it == submissions.end()) {
        return "";
    }
    
    TransactionHash challengeId = "challenge_" + submissionId + "_" + std::to_string(std::time(nullptr));
    challenges[challengeId] = false;  // Pending resolution
    
    recordAction("challenge_verification", challenger, submissionId);
    
    return challengeId;
}

std::vector<TransactionHash> OracleContract::getPendingChallenges() const {
    std::vector<TransactionHash> result;
    for (const auto& challenge : challenges) {
        if (!challenge.second) {  // false = unresolved
            result.push_back(challenge.first);
        }
    }
    return result;
}

bool OracleContract::resolveChallenge(const TransactionHash& challengeId, bool accepted) {
    auto it = challenges.find(challengeId);
    if (it == challenges.end()) {
        return false;
    }
    
    it->second = true;  // Mark as resolved
    return true;
}

bool OracleContract::registerWithDao(const TransactionHash& submissionId) {
    auto it = submissions.find(submissionId);
    if (it == submissions.end()) {
        return false;
    }
    
    if (it->second.verificationLevel < VerificationLevel::ADVANCED) {
        return false;
    }
    
    // Register with DAO
    std::vector<CategoryScore> scores = it->second.scores;
    return daoContract->submitCompositeScore(it->second.targetContributor, scores);
}

bool OracleContract::isRegisteredWithDao(const TransactionHash& submissionId) const {
    auto it = submissions.find(submissionId);
    if (it != submissions.end()) {
        return it->second.verificationLevel >= VerificationLevel::ADVANCED;
    }
    return false;
}

OracleContract::Statistics OracleContract::getStatistics() const {
    Statistics stats;
    stats.totalSubmissions = submissions.size();
    stats.verifiedSubmissions = 0;
    stats.pendingSubmissions = 0;
    stats.rejectedSubmissions = 0;
    stats.totalVerifiers = verifiers.size();
    stats.pendingChallenges = getPendingChallenges().size();
    stats.averageVerificationTime = getAverageVerificationTime();
    
    for (const auto& sub : submissions) {
        if (sub.second.verificationLevel == VerificationLevel::AUDIT_COMPLETE) {
            stats.verifiedSubmissions++;
        } else if (sub.second.verificationLevel == VerificationLevel::UNVERIFIED) {
            stats.pendingSubmissions++;
        }
    }
    
    return stats;
}

uint64 OracleContract::getAverageVerificationTime() const {
    if (verificationChains.empty()) {
        return 0;
    }
    
    uint64 totalTime = 0;
    uint64 count = 0;
    
    for (const auto& chain : verificationChains) {
        if (!chain.second.empty()) {
            uint64 startTime = submissions.find(chain.first)->second.submittedAt;
            uint64 endTime = chain.second.back().verifiedAt;
            if (endTime > startTime) {
                totalTime += (endTime - startTime);
                count++;
            }
        }
    }
    
    return count > 0 ? totalTime / count : 0;
}

uint8 OracleContract::getAcceptanceRate() const {
    if (totalVerifications == 0) {
        return 0;
    }
    
    return static_cast<uint8>((acceptedVerifications * 100) / totalVerifications);
}

Hash256 OracleContract::computeMerkleTree(const OracleSubmission& submission) const {
    Hash256 result{};
    
    size_t pos = 0;
    for (const auto& score : submission.scores) {
        result[pos % 32] ^= static_cast<uint8>(score.score);
        pos++;
    }
    
    for (size_t i = 0; i < 20; ++i) {
        result[i] ^= submission.gitSHA1[i];
    }
    
    return result;
}

bool OracleContract::validateScores(uint8 cq, uint8 doc, uint8 test, uint8 innov, uint8 comm) const {
    return isValidScore(cq) && isValidScore(doc) && isValidScore(test) && 
           isValidScore(innov) && isValidScore(comm);
}

TransactionHash OracleContract::generateSubmissionId() const {
    return "sub_" + std::to_string(std::time(nullptr));
}

}  // namespace UCIC
