# UCIC DAO - On-Chain Implementation Guide

## Overview

This document outlines the on-chain components required to deploy the **Ubuntu Code Integrity Crucible (UCIC) DAO** on the Qubic blockchain for the hackathon submission.

**DAO Purpose:** Reward top 3 monthly contributors with UC tokens based on transparent, automated QUBIC scoring.

---

## On-Chain Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    UCIC DAO Smart Contract                   │
├─────────────────────────────────────────────────────────────┤
│  • UC Token Management (1000 UC initial supply)             │
│  • Monthly Reward Distribution (automated)                   │
│  • Governance Voting (tier-based voting power)              │
│  • Treasury Management (multi-sig security)                  │
│  • Audit Trail (immutable on-chain records)                 │
└─────────────────────────────────────────────────────────────┘
         ↓                    ↓                    ↓
   [UC Token]          [Governance]         [Treasury]
```

---

## Phase 1: UC Token Deployment

### Token Specifications

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Name** | Ubuntu Code Token | Clear identity |
| **Symbol** | UC | Short, memorable |
| **Initial Supply** | 1,000 UC | Hackathon requirement |
| **Decimals** | 18 | Standard ERC-20 compatibility |
| **Type** | Governance + Utility | Voting + rewards |
| **Mintable** | Yes (DAO vote required) | Future scalability |
| **Burnable** | No | Preserve scarcity |

### Smart Contract: UC Token

```javascript
// Qubic Smart Contract (QPI-compatible)
// File: contracts/UCToken.qsc

contract UCToken {
    // Token metadata
    string public name = "Ubuntu Code Token";
    string public symbol = "UC";
    uint8 public decimals = 18;
    uint256 public totalSupply = 1000 * 10**18; // 1000 UC
    
    // Balances and allowances
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    
    // DAO governance
    address public daoContract;
    bool public mintingEnabled = true;
    
    // Events
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event Mint(address indexed to, uint256 amount);
    
    // Constructor - Initialize DAO treasury
    constructor(address _daoTreasury) {
        balanceOf[_daoTreasury] = totalSupply;
        daoContract = msg.sender;
        emit Transfer(address(0), _daoTreasury, totalSupply);
    }
    
    // Standard ERC-20 functions
    function transfer(address _to, uint256 _value) public returns (bool) {
        require(balanceOf[msg.sender] >= _value, "Insufficient balance");
        balanceOf[msg.sender] -= _value;
        balanceOf[_to] += _value;
        emit Transfer(msg.sender, _to, _value);
        return true;
    }
    
    function approve(address _spender, uint256 _value) public returns (bool) {
        allowance[msg.sender][_spender] = _value;
        emit Approval(msg.sender, _spender, _value);
        return true;
    }
    
    function transferFrom(address _from, address _to, uint256 _value) public returns (bool) {
        require(balanceOf[_from] >= _value, "Insufficient balance");
        require(allowance[_from][msg.sender] >= _value, "Allowance exceeded");
        balanceOf[_from] -= _value;
        balanceOf[_to] += _value;
        allowance[_from][msg.sender] -= _value;
        emit Transfer(_from, _to, _value);
        return true;
    }
    
    // DAO-only minting (requires governance vote)
    function mint(address _to, uint256 _amount) public {
        require(msg.sender == daoContract, "Only DAO can mint");
        require(mintingEnabled, "Minting disabled");
        totalSupply += _amount;
        balanceOf[_to] += _amount;
        emit Mint(_to, _amount);
        emit Transfer(address(0), _to, _amount);
    }
}
```

### Deployment Steps

1. **Compile Contract**
   ```bash
   qubic-cli compile contracts/UCToken.qsc
   ```

2. **Deploy to Qubic Testnet**
   ```bash
   qubic-cli deploy UCToken \
     --network testnet \
     --treasury 0xDAO_TREASURY_ADDRESS \
     --gas-limit 5000000
   ```

3. **Verify Deployment**
   ```bash
   qubic-cli verify UCToken \
     --address 0xDEPLOYED_CONTRACT_ADDRESS \
     --network testnet
   ```

4. **Record Contract Address**
   - Save to `.env` file
   - Update documentation
   - Publish to community

---

## Phase 2: DAO Governance Contract

### Smart Contract: UCIC DAO

```javascript
// File: contracts/UCIC_DAO.qsc

contract UCIC_DAO {
    // DAO configuration
    UCToken public ucToken;
    address public founder1; // Dr. Jodogn
    address public founder2; // Master Tom
    
    // Treasury management
    uint256 public monthlyRewardPool = 30 * 10**18; // 30 UC per month
    uint256 public lastRewardDistribution;
    
    // Contributor tiers (QUBIC scores)
    enum Tier { None, Recognized, Bronze, Silver, Gold, Platinum }
    
    struct Contributor {
        address wallet;
        uint256 qubicScore;
        Tier tier;
        uint256 lastContributionDate;
        uint256 totalRewardsEarned;
    }
    
    mapping(address => Contributor) public contributors;
    address[] public contributorList;
    
    // Governance proposals
    struct Proposal {
        uint256 id;
        string description;
        address proposer;
        uint256 votesFor;
        uint256 votesAgainst;
        uint256 startTime;
        uint256 endTime;
        bool executed;
        ProposalType proposalType;
    }
    
    enum ProposalType { Tactical, Strategic, Critical }
    
    mapping(uint256 => Proposal) public proposals;
    uint256 public proposalCount;
    
    // Voting power multipliers by tier
    mapping(Tier => uint256) public votingMultiplier;
    
    // Events
    event ContributorRegistered(address indexed contributor, uint256 qubicScore, Tier tier);
    event RewardsDistributed(address[3] topContributors, uint256[3] amounts);
    event ProposalCreated(uint256 indexed proposalId, address proposer, string description);
    event VoteCast(uint256 indexed proposalId, address voter, bool support, uint256 votingPower);
    event ProposalExecuted(uint256 indexed proposalId);
    
    // Constructor
    constructor(address _ucToken, address _founder1, address _founder2) {
        ucToken = UCToken(_ucToken);
        founder1 = _founder1;
        founder2 = _founder2;
        lastRewardDistribution = block.timestamp;
        
        // Set voting multipliers
        votingMultiplier[Tier.None] = 5; // 0.5x (token holders)
        votingMultiplier[Tier.Recognized] = 10; // 1x
        votingMultiplier[Tier.Bronze] = 10; // 1x
        votingMultiplier[Tier.Silver] = 20; // 2x
        votingMultiplier[Tier.Gold] = 30; // 3x
        votingMultiplier[Tier.Platinum] = 50; // 5x
    }
    
    // Register contributor with QUBIC score
    function registerContributor(
        address _contributor,
        uint256 _qubicScore
    ) public onlyFounders {
        require(_qubicScore >= 50, "Minimum score 50 required");
        
        Tier tier = calculateTier(_qubicScore);
        
        contributors[_contributor] = Contributor({
            wallet: _contributor,
            qubicScore: _qubicScore,
            tier: tier,
            lastContributionDate: block.timestamp,
            totalRewardsEarned: 0
        });
        
        contributorList.push(_contributor);
        
        emit ContributorRegistered(_contributor, _qubicScore, tier);
    }
    
    // Calculate tier from QUBIC score
    function calculateTier(uint256 _score) internal pure returns (Tier) {
        if (_score >= 90) return Tier.Platinum;
        if (_score >= 80) return Tier.Gold;
        if (_score >= 70) return Tier.Silver;
        if (_score >= 60) return Tier.Bronze;
        return Tier.Recognized;
    }
    
    // Distribute monthly rewards (automated)
    function distributeMonthlyRewards() public {
        require(
            block.timestamp >= lastRewardDistribution + 30 days,
            "Too early for next distribution"
        );
        
        // Get top 3 contributors by QUBIC score
        address[3] memory topContributors = getTop3Contributors();
        
        // Calculate reward distribution (50%, 30%, 20%)
        uint256[3] memory rewards = [
            (monthlyRewardPool * 50) / 100,
            (monthlyRewardPool * 30) / 100,
            (monthlyRewardPool * 20) / 100
        ];
        
        // Transfer rewards
        for (uint i = 0; i < 3; i++) {
            if (topContributors[i] != address(0)) {
                ucToken.transfer(topContributors[i], rewards[i]);
                contributors[topContributors[i]].totalRewardsEarned += rewards[i];
            }
        }
        
        lastRewardDistribution = block.timestamp;
        
        emit RewardsDistributed(topContributors, rewards);
    }
    
    // Get top 3 contributors by QUBIC score
    function getTop3Contributors() public view returns (address[3] memory) {
        address[3] memory top3;
        uint256[3] memory topScores;
        
        for (uint i = 0; i < contributorList.length; i++) {
            address contributor = contributorList[i];
            uint256 score = contributors[contributor].qubicScore;
            
            // Check if score qualifies for top 3
            for (uint j = 0; j < 3; j++) {
                if (score > topScores[j]) {
                    // Shift lower scores down
                    for (uint k = 2; k > j; k--) {
                        topScores[k] = topScores[k-1];
                        top3[k] = top3[k-1];
                    }
                    // Insert new top score
                    topScores[j] = score;
                    top3[j] = contributor;
                    break;
                }
            }
        }
        
        return top3;
    }
    
    // Create governance proposal
    function createProposal(
        string memory _description,
        ProposalType _type
    ) public returns (uint256) {
        require(
            contributors[msg.sender].tier != Tier.None || 
            ucToken.balanceOf(msg.sender) > 0,
            "Must be contributor or token holder"
        );
        
        proposalCount++;
        
        uint256 votingPeriod = _type == ProposalType.Tactical ? 7 days : 14 days;
        
        proposals[proposalCount] = Proposal({
            id: proposalCount,
            description: _description,
            proposer: msg.sender,
            votesFor: 0,
            votesAgainst: 0,
            startTime: block.timestamp,
            endTime: block.timestamp + votingPeriod,
            executed: false,
            proposalType: _type
        });
        
        emit ProposalCreated(proposalCount, msg.sender, _description);
        
        return proposalCount;
    }
    
    // Cast vote on proposal
    function vote(uint256 _proposalId, bool _support) public {
        Proposal storage proposal = proposals[_proposalId];
        
        require(block.timestamp <= proposal.endTime, "Voting ended");
        require(!proposal.executed, "Already executed");
        
        // Calculate voting power
        uint256 votingPower = calculateVotingPower(msg.sender);
        require(votingPower > 0, "No voting power");
        
        if (_support) {
            proposal.votesFor += votingPower;
        } else {
            proposal.votesAgainst += votingPower;
        }
        
        emit VoteCast(_proposalId, msg.sender, _support, votingPower);
    }
    
    // Calculate voting power based on tier and token holdings
    function calculateVotingPower(address _voter) public view returns (uint256) {
        uint256 tokenBalance = ucToken.balanceOf(_voter);
        Tier tier = contributors[_voter].tier;
        uint256 multiplier = votingMultiplier[tier];
        
        return (tokenBalance * multiplier) / 10; // Divide by 10 for decimal precision
    }
    
    // Execute approved proposal
    function executeProposal(uint256 _proposalId) public {
        Proposal storage proposal = proposals[_proposalId];
        
        require(block.timestamp > proposal.endTime, "Voting still active");
        require(!proposal.executed, "Already executed");
        
        // Check quorum and approval threshold
        uint256 totalVotes = proposal.votesFor + proposal.votesAgainst;
        uint256 quorum = proposal.proposalType == ProposalType.Tactical ? 20 : 40;
        uint256 threshold = proposal.proposalType == ProposalType.Strategic ? 66 : 51;
        
        require(totalVotes >= (ucToken.totalSupply() * quorum) / 100, "Quorum not met");
        require(
            (proposal.votesFor * 100) / totalVotes >= threshold,
            "Threshold not met"
        );
        
        // For critical proposals, require founder approval
        if (proposal.proposalType == ProposalType.Critical) {
            require(
                msg.sender == founder1 || msg.sender == founder2,
                "Founder approval required"
            );
        }
        
        proposal.executed = true;
        
        emit ProposalExecuted(_proposalId);
    }
    
    // Modifiers
    modifier onlyFounders() {
        require(
            msg.sender == founder1 || msg.sender == founder2,
            "Only founders"
        );
        _;
    }
}
```

### Deployment Steps

1. **Deploy DAO Contract**
   ```bash
   qubic-cli deploy UCIC_DAO \
     --network testnet \
     --uc-token 0xUC_TOKEN_ADDRESS \
     --founder1 0xFOUNDER1_ADDRESS \
     --founder2 0xFOUNDER2_ADDRESS \
     --gas-limit 10000000
   ```

2. **Transfer Treasury to DAO**
   ```bash
   qubic-cli execute UCToken.transfer \
     --to 0xDAO_CONTRACT_ADDRESS \
     --amount 1000000000000000000000 \
     --network testnet
   ```

3. **Verify DAO Setup**
   ```bash
   qubic-cli call UCIC_DAO.ucToken
   qubic-cli call UCIC_DAO.monthlyRewardPool
   ```

---

## Phase 3: Oracle Integration (Off-chain → On-chain)

### QUBIC Score Oracle

The oracle bridges off-chain QUBIC scores to on-chain contributor registration.

```javascript
// File: contracts/QUBICOracle.qsc

contract QUBICOracle {
    UCIC_DAO public dao;
    address public oracleOperator;
    
    struct ScoreUpdate {
        address contributor;
        uint256 qubicScore;
        uint256 timestamp;
        string githubCommitHash;
        bool verified;
    }
    
    mapping(address => ScoreUpdate) public latestScores;
    
    event ScoreSubmitted(address indexed contributor, uint256 score, string commitHash);
    event ScoreVerified(address indexed contributor, uint256 score);
    
    constructor(address _dao, address _operator) {
        dao = UCIC_DAO(_dao);
        oracleOperator = _operator;
    }
    
    // Submit QUBIC score from off-chain analysis
    function submitScore(
        address _contributor,
        uint256 _qubicScore,
        string memory _githubCommitHash
    ) public onlyOperator {
        require(_qubicScore >= 50 && _qubicScore <= 100, "Invalid score range");
        
        latestScores[_contributor] = ScoreUpdate({
            contributor: _contributor,
            qubicScore: _qubicScore,
            timestamp: block.timestamp,
            githubCommitHash: _githubCommitHash,
            verified: false
        });
        
        emit ScoreSubmitted(_contributor, _qubicScore, _githubCommitHash);
    }
    
    // Verify and register contributor in DAO
    function verifyAndRegister(address _contributor) public onlyOperator {
        ScoreUpdate storage update = latestScores[_contributor];
        require(!update.verified, "Already verified");
        require(update.qubicScore > 0, "No score submitted");
        
        // Register in DAO
        dao.registerContributor(_contributor, update.qubicScore);
        
        update.verified = true;
        
        emit ScoreVerified(_contributor, update.qubicScore);
    }
    
    modifier onlyOperator() {
        require(msg.sender == oracleOperator, "Only oracle operator");
        _;
    }
}
```

### Oracle Deployment

```bash
qubic-cli deploy QUBICOracle \
  --network testnet \
  --dao 0xDAO_CONTRACT_ADDRESS \
  --operator 0xORACLE_OPERATOR_ADDRESS
```

---

## Phase 4: Frontend Integration

### Web3 Connection

```javascript
// File: qubic-hackathon/web3/dao-interface.js

import { QubicProvider } from '@qubic/web3';

class DAOInterface {
    constructor(contractAddress) {
        this.provider = new QubicProvider('https://testnet.qubic.org');
        this.daoContract = this.provider.getContract(contractAddress, DAO_ABI);
    }
    
    // Get top 3 contributors
    async getTop3Contributors() {
        return await this.daoContract.getTop3Contributors();
    }
    
    // Get contributor info
    async getContributor(address) {
        return await this.daoContract.contributors(address);
    }
    
    // Create proposal
    async createProposal(description, type) {
        const tx = await this.daoContract.createProposal(description, type);
        return await tx.wait();
    }
    
    // Vote on proposal
    async vote(proposalId, support) {
        const tx = await this.daoContract.vote(proposalId, support);
        return await tx.wait();
    }
    
    // Check if rewards can be distributed
    async canDistributeRewards() {
        const lastDistribution = await this.daoContract.lastRewardDistribution();
        const now = Math.floor(Date.now() / 1000);
        return now >= lastDistribution + (30 * 24 * 60 * 60);
    }
    
    // Distribute monthly rewards
    async distributeRewards() {
        const tx = await this.daoContract.distributeMonthlyRewards();
        return await tx.wait();
    }
}

export default DAOInterface;
```

---

## Phase 5: Testing & Validation

### Test Scenarios

1. **Token Deployment**
   - ✅ Deploy UC token with 1000 supply
   - ✅ Verify treasury receives all tokens
   - ✅ Test transfer functionality

2. **DAO Initialization**
   - ✅ Deploy DAO contract
   - ✅ Link to UC token
   - ✅ Set founder addresses
   - ✅ Configure voting multipliers

3. **Contributor Registration**
   - ✅ Register contributor with score 95 (Platinum)
   - ✅ Register contributor with score 85 (Gold)
   - ✅ Register contributor with score 75 (Silver)
   - ✅ Verify tier assignment

4. **Reward Distribution**
   - ✅ Wait 30 days (or fast-forward in testnet)
   - ✅ Call distributeMonthlyRewards()
   - ✅ Verify top 3 receive 50%, 30%, 20%
   - ✅ Check balances updated

5. **Governance Voting**
   - ✅ Create tactical proposal
   - ✅ Cast votes from different tiers
   - ✅ Verify voting power calculation
   - ✅ Execute approved proposal

### Test Script

```bash
# File: scripts/test-dao.sh

#!/bin/bash

echo "Testing UCIC DAO on Qubic Testnet..."

# 1. Deploy contracts
echo "Deploying UC Token..."
UC_TOKEN=$(qubic-cli deploy UCToken --network testnet --output address)

echo "Deploying DAO..."
DAO=$(qubic-cli deploy UCIC_DAO --uc-token $UC_TOKEN --network testnet --output address)

# 2. Register test contributors
echo "Registering contributors..."
qubic-cli execute $DAO.registerContributor --contributor 0xTEST1 --score 95
qubic-cli execute $DAO.registerContributor --contributor 0xTEST2 --score 85
qubic-cli execute $DAO.registerContributor --contributor 0xTEST3 --score 75

# 3. Check top 3
echo "Checking top 3 contributors..."
qubic-cli call $DAO.getTop3Contributors

# 4. Fast-forward time (testnet only)
echo "Fast-forwarding 30 days..."
qubic-cli testnet fast-forward --days 30

# 5. Distribute rewards
echo "Distributing monthly rewards..."
qubic-cli execute $DAO.distributeMonthlyRewards

# 6. Verify balances
echo "Verifying balances..."
qubic-cli call $UC_TOKEN.balanceOf --address 0xTEST1
qubic-cli call $UC_TOKEN.balanceOf --address 0xTEST2
qubic-cli call $UC_TOKEN.balanceOf --address 0xTEST3

echo "✅ DAO testing complete!"
```

---

## Phase 6: Mainnet Deployment Checklist

### Pre-Deployment

- [ ] Security audit completed
- [ ] Testnet testing passed (all scenarios)
- [ ] Founder wallets secured (hardware wallets)
- [ ] Treasury multi-sig configured
- [ ] Oracle operator identified
- [ ] Community notified (7 days advance)

### Deployment

- [ ] Deploy UC Token to mainnet
- [ ] Deploy UCIC DAO to mainnet
- [ ] Deploy QUBICOracle to mainnet
- [ ] Transfer 1000 UC to DAO treasury
- [ ] Verify all contracts on Qubic Explorer
- [ ] Test one complete reward cycle

### Post-Deployment

- [ ] Publish contract addresses
- [ ] Update frontend with mainnet contracts
- [ ] Create governance documentation
- [ ] Announce to community
- [ ] Schedule first monthly distribution
- [ ] Monitor for 30 days

---

## Security Considerations

### Multi-Sig Treasury

```javascript
// Recommended: Use Gnosis Safe or equivalent on Qubic
// Require 2-of-3 signatures for treasury operations:
// - Founder 1 (Dr. Jodogn)
// - Founder 2 (Master Tom)
// - Community Representative (elected)
```

### Access Controls

| Function | Access Level | Rationale |
|----------|--------------|-----------|
| `registerContributor()` | Founders only | Prevent score manipulation |
| `distributeMonthlyRewards()` | Anyone | Automated, trustless |
| `createProposal()` | Contributors + token holders | Democratic |
| `vote()` | Contributors + token holders | Democratic |
| `executeProposal()` | Anyone (if approved) | Trustless execution |
| `mint()` | DAO only (via vote) | Controlled inflation |

### Audit Trail

Every on-chain action creates:
1. **Transaction hash** - Immutable proof
2. **Event logs** - Searchable history
3. **Block timestamp** - Temporal ordering
4. **Gas costs** - Economic accountability

---

## Cost Estimates

### Deployment Costs (Qubic Testnet → Mainnet)

| Contract | Estimated Gas | Cost (QUBIC) |
|----------|---------------|--------------|
| UC Token | 2,000,000 | ~0.5 QUBIC |
| UCIC DAO | 5,000,000 | ~1.2 QUBIC |
| QUBICOracle | 1,500,000 | ~0.4 QUBIC |
| **Total** | **8,500,000** | **~2.1 QUBIC** |

### Monthly Operating Costs

| Operation | Frequency | Cost per Month |
|-----------|-----------|----------------|
| Reward distribution | 1x/month | ~0.1 QUBIC |
| Score updates | ~10x/month | ~0.5 QUBIC |
| Governance votes | ~2x/month | ~0.2 QUBIC |
| **Total** | - | **~0.8 QUBIC/month** |

---

## Integration with Off-Chain QUBIC System

### Data Flow

```
1. Contributor submits code → GitHub
2. QUBIC analyzer runs → Generates score
3. Score recorded in Git → Audit trail
4. Oracle operator submits score → On-chain
5. DAO registers contributor → Tier assigned
6. Monthly: DAO distributes rewards → Automated
7. Certificate generated → Off-chain + QR code links to on-chain proof
```

### Synchronization

```python
# File: scripts/sync-scores-onchain.py

from web3 import Web3
from qubic_analyzer import QUBICAnalyzer

# Connect to Qubic
w3 = Web3(Web3.HTTPProvider('https://mainnet.qubic.org'))
oracle = w3.eth.contract(address=ORACLE_ADDRESS, abi=ORACLE_ABI)

# Get latest QUBIC scores from Git
analyzer = QUBICAnalyzer()
scores = analyzer.get_monthly_scores()

# Submit to oracle
for contributor, score in scores.items():
    commit_hash = analyzer.get_commit_hash(contributor)
    tx = oracle.functions.submitScore(
        contributor,
        score,
        commit_hash
    ).transact({'from': ORACLE_OPERATOR})
    
    print(f"Submitted {contributor}: {score} (tx: {tx.hex()})")
```

---

## Monitoring & Maintenance

### Dashboard Metrics

Track on-chain:
- Total UC tokens in circulation
- Number of registered contributors
- Monthly reward distributions
- Active governance proposals
- Voting participation rate
- Treasury balance

### Alerts

Set up notifications for:
- Reward distribution due (every 30 days)
- New proposals created
- Proposals ready for execution
- Low treasury balance (<100 UC)
- Unusual voting patterns

---

## Community Resources

### For Contributors

- **Check your tier:** `https://qubic-explorer.org/address/YOUR_ADDRESS`
- **View leaderboard:** `https://ubuntu-patient-care.org/qubic/leaderboard`
- **Track rewards:** `https://ubuntu-patient-care.org/qubic/rewards`

### For Token Holders

- **Vote on proposals:** `https://ubuntu-patient-care.org/qubic/governance`
- **View treasury:** `https://qubic-explorer.org/address/DAO_TREASURY`
- **Audit trail:** All transactions public on Qubic Explorer

---

## Next Steps

1. **Week 1:** Deploy to Qubic Testnet
2. **Week 2:** Test all scenarios, fix bugs
3. **Week 3:** Security audit, community review
4. **Week 4:** Mainnet deployment
5. **Month 1:** First reward distribution
6. **Ongoing:** Monthly operations, governance

---

## Support & Documentation

- **Qubic Docs:** https://docs.qubic.org
- **Smart Contract Code:** `qubic-hackathon/contracts/`
- **Test Scripts:** `qubic-hackathon/scripts/`
- **Frontend Integration:** `qubic-hackathon/web3/`

---

## License

Open Source - MIT License

**Built for the Qubic Hackathon 2025**  
**Ubuntu Patient Care - Ubuntu Code Integrity Crucible (UCIC)**

---

*"Transparent scoring, automated rewards, on-chain proof."*
