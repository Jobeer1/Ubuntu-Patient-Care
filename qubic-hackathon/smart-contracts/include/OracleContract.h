#pragma once

#include "types.h"
#include "UCTokenContract.h"
#include "UCICDaoContract.h"
#include <vector>
#include <map>
#include <set>
#include <memory>

namespace UCIC {

/**
 * Oracle Contract
 * 
 * Multi-stage verification system for contributor scores
 * Ensures quality, transparency, and audit trail
 * Features:
 *  - Multi-tier verification process
 *  - Git repository linking and SHA-1 verification
 *  - Merkle tree proofs for data integrity
 *  - BLAKE3 hash verification
 *  - Comprehensive audit logging
 */
class OracleContract {
public:
    // ========================================================================
    // CONSTRUCTOR & LIFECYCLE
    // ========================================================================
    
    OracleContract(std::shared_ptr<UCICDaoContract> daoContract);
    ~OracleContract() = default;
    
    // ========================================================================
    // SUBMISSION & VERIFICATION
    // ========================================================================
    
    /**
     * Submit scores for a contributor
     * Initial submission with supporting evidence
     * @param contributor Target contributor address
     * @param codeQuality Code quality score (0-100)
     * @param documentation Documentation quality (0-100)
     * @param testing Test coverage and quality (0-100)
     * @param innovation Innovation and originality (0-100)
     * @param community Community impact (0-100)
     * @param gitRepository Git repository URL/hash
     * @param evidenceHash BLAKE3 hash of evidence
     * @return Submission ID if successful, empty string on failure
     */
    TransactionHash submitScore(const PublicAddress& contributor,
                               uint8 codeQuality,
                               uint8 documentation,
                               uint8 testing,
                               uint8 innovation,
                               uint8 community,
                               const std::string& gitRepository,
                               const Hash256& evidenceHash);
    
    /**
     * Verify a submitted score
     * Called by authorized verifiers (minimum 3 required for completion)
     * @param submissionId ID of submission to verify
     * @param verifier Address of verifying entity
     * @param approved True to approve, false to reject
     * @param notes Verification notes
     * @return Success status
     */
    bool verifySubmission(const TransactionHash& submissionId,
                         const PublicAddress& verifier,
                         bool approved,
                         const std::string& notes);
    
    /**
     * Get submission details
     * @param submissionId Submission ID to retrieve
     * @return OracleSubmission structure if exists
     */
    OracleSubmission getSubmission(const TransactionHash& submissionId) const;
    
    /**
     * Get submissions for a contributor
     * @param contributor Contributor address
     * @return Vector of submission IDs for that contributor
     */
    std::vector<TransactionHash> getSubmissionsForContributor(
        const PublicAddress& contributor) const;
    
    /**
     * Get verification status of submission
     * @param submissionId Submission ID
     * @return Current verification level
     */
    VerificationLevel getVerificationStatus(const TransactionHash& submissionId) const;
    
    // ========================================================================
    // GIT INTEGRATION
    // ========================================================================
    
    /**
     * Link Git repository to contributor
     * Enables verification via Git history
     * @param contributor Contributor address
     * @param repoUrl Git repository URL
     * @param commitSha Latest commit SHA-1 hash
     * @return Success status
     */
    bool linkGitRepository(const PublicAddress& contributor,
                          const std::string& repoUrl,
                          const GitHash& commitSha);
    
    /**
     * Get linked Git repository for contributor
     * @param contributor Contributor address
     * @return Repository URL if linked
     */
    std::string getLinkedRepository(const PublicAddress& contributor) const;
    
    /**
     * Verify Git commit
     * Confirms contributor has actual code/documentation in repository
     * @param repoUrl Repository URL
     * @param commitSha Commit SHA to verify
     * @return True if commit exists and is valid
     */
    bool verifyGitCommit(const std::string& repoUrl, const GitHash& commitSha) const;
    
    // ========================================================================
    // MERKLE TREE VERIFICATION
    // ========================================================================
    
    /**
     * Create Merkle proof for submission
     * Enables cryptographic verification of submission data
     * @param submissionId Submission to create proof for
     * @return Merkle root hash
     */
    Hash256 createMerkleProof(const TransactionHash& submissionId);
    
    /**
     * Verify Merkle proof
     * Confirms data integrity using Merkle tree
     * @param submissionId Submission ID
     * @param merkleRoot Root hash to verify against
     * @return True if proof is valid
     */
    bool verifyMerkleProof(const TransactionHash& submissionId,
                          const Hash256& merkleRoot) const;
    
    /**
     * Get Merkle root for submission
     * @param submissionId Submission ID
     * @return Merkle root hash if proof exists
     */
    Hash256 getMerkleRoot(const TransactionHash& submissionId) const;
    
    // ========================================================================
    // CRYPTO VERIFICATION (BLAKE3)
    // ========================================================================
    
    /**
     * Compute BLAKE3 hash of data
     * Fast, secure cryptographic hash
     * @param data Input data
     * @return BLAKE3 hash (256-bit)
     */
    Hash256 computeBlake3Hash(const std::string& data) const;
    
    /**
     * Verify BLAKE3 hash
     * @param data Original data
     * @param expectedHash Expected hash value
     * @return True if hash matches
     */
    bool verifyBlake3Hash(const std::string& data, 
                         const Hash256& expectedHash) const;
    
    // ========================================================================
    // AUDIT TRAIL & TRANSPARENCY
    // ========================================================================
    
    /**
     * Get audit trail for a submission
     * All verification actions and verifiers
     * @param submissionId Submission ID
     * @return Vector of verification records
     */
    struct VerificationRecord {
        PublicAddress verifier;
        bool approved;
        std::string notes;
        Timestamp verifiedAt;
    };
    
    /**
     * Get verification chain for submission
     * @param submissionId Submission ID
     * @return Vector of all verification records in order
     */
    std::vector<VerificationRecord> getVerificationChain(
        const TransactionHash& submissionId) const;
    
    /**
     * Record oracle action
     * @param action Description of action
     * @param actor Address performing action
     * @param submissionId Associated submission
     * @return Transaction hash of this recording
     */
    TransactionHash recordAction(const std::string& action,
                                const PublicAddress& actor,
                                const TransactionHash& submissionId);
    
    // ========================================================================
    // VERIFIER MANAGEMENT
    // ========================================================================
    
    /**
     * Register as verifier
     * @param address Address requesting verifier role
     * @return Success status
     */
    bool registerVerifier(const PublicAddress& address);
    
    /**
     * Check if address is authorized verifier
     * @param address Address to check
     * @return True if address is verifier
     */
    bool isVerifier(const PublicAddress& address) const;
    
    /**
     * Get list of active verifiers
     * @return Vector of verifier addresses
     */
    std::vector<PublicAddress> getVerifiers() const;
    
    /**
     * Get verifier statistics
     * @param verifier Verifier address
     * @return Number of verifications completed
     */
    uint64 getVerifierStats(const PublicAddress& verifier) const;
    
    /**
     * Remove verifier (governance only)
     * @param address Verifier to remove
     * @return Success status
     */
    bool removeVerifier(const PublicAddress& address);
    
    // ========================================================================
    // DISPUTE RESOLUTION
    // ========================================================================
    
    /**
     * Challenge a verification
     * Dispute verification if believe it's incorrect
     * @param submissionId Submission to challenge
     * @param challenger Address challenging
     * @param reason Reason for challenge
     * @return Challenge ID if successful
     */
    TransactionHash challengeVerification(const TransactionHash& submissionId,
                                         const PublicAddress& challenger,
                                         const std::string& reason);
    
    /**
     * Get pending challenges
     * @return Vector of submission IDs with active challenges
     */
    std::vector<TransactionHash> getPendingChallenges() const;
    
    /**
     * Resolve challenge
     * Governance decision on disputed verification
     * @param challengeId Challenge to resolve
     * @param accepted True if challenge accepted, false if verification stands
     * @return Success status
     */
    bool resolveChallenge(const TransactionHash& challengeId, bool accepted);
    
    // ========================================================================
    // DAO INTEGRATION
    // ========================================================================
    
    /**
     * Register verified scores with DAO
     * Push approved verification data to DAO
     * @param submissionId Submission to register
     * @return Success status
     */
    bool registerWithDao(const TransactionHash& submissionId);
    
    /**
     * Get DAO registration status
     * @param submissionId Submission to check
     * @return True if registered with DAO
     */
    bool isRegisteredWithDao(const TransactionHash& submissionId) const;
    
    // ========================================================================
    // STATISTICS & REPORTING
    // ========================================================================
    
    /**
     * Get oracle statistics
     */
    struct Statistics {
        uint64 totalSubmissions;
        uint64 verifiedSubmissions;
        uint64 pendingSubmissions;
        uint64 rejectedSubmissions;
        uint64 totalVerifiers;
        uint64 pendingChallenges;
        uint64 averageVerificationTime;
    };
    
    /**
     * Get current oracle statistics
     * @return Statistics structure
     */
    Statistics getStatistics() const;
    
    /**
     * Get verification timeline
     * Average time from submission to verification
     * @return Time in seconds
     */
    uint64 getAverageVerificationTime() const;
    
    /**
     * Get acceptance rate
     * Percentage of submissions accepted
     * @return Acceptance rate 0-100
     */
    uint8 getAcceptanceRate() const;

private:
    std::shared_ptr<UCICDaoContract> daoContract;
    
    // Core data structures
    std::map<TransactionHash, OracleSubmission> submissions;
    std::map<TransactionHash, std::vector<VerificationRecord>> verificationChains;
    std::map<PublicAddress, std::string> gitRepositories;
    std::map<TransactionHash, Hash256> merkleRoots;
    std::set<PublicAddress> verifiers;
    std::vector<TransactionHash> auditLog;
    
    // Challenge tracking
    std::map<TransactionHash, bool> challenges;
    
    uint64 totalVerifications;
    uint64 acceptedVerifications;
    
    // Helper methods
    Hash256 computeMerkleTree(const OracleSubmission& submission) const;
    bool validateScores(uint8 cq, uint8 doc, uint8 test, uint8 innov, uint8 comm) const;
    TransactionHash generateSubmissionId() const;
};

}  // namespace UCIC

#endif  // ORACLECONTRACT_H
