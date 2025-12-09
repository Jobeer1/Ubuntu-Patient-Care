# Smart Contracts for Healthcare Compute Platform

These smart contracts run on the Qubic blockchain and manage the decentralized compute marketplace.

## Contract Overview

### 1. ComputeMarketplace.sol
- Manages job submission and bidding
- Handles compute credit allocation
- Tracks job status and completion
- Implements dispute resolution

### 2. MedicalDataAccess.sol
- Manages consent for data access
- Tracks data usage permissions
- Implements privacy controls
- Maintains audit trails

### 3. ResultVerification.sol
- Handles result validation
- Implements k-of-n verification
- Manages verification rewards
- Tracks reputation scores

## Deployment

### Prerequisites
- Node.js 16+
- Qubic SDK
- Test UC tokens (for testnet)

### Deploy to Testnet

```bash
# Install dependencies
npm install

# Set environment variables
export QUBIC_RPC_URL=https://testnet.rpc.qubic.org
export PRIVATE_KEY=your-testnet-private-key

# Compile contracts
npm run compile

# Deploy contracts
npm run deploy:testnet

# Verify contracts (optional)
npm run verify:testnet
```

## Configuration

Update `config/testnet.json` with your deployment settings:

```json
{
  "network": "testnet",
  "rpcUrl": "https://testnet.rpc.qubic.org",
  "gasPrice": "1000000000",
  "confirmations": 2,
  "timeout": 300
}
```

## Interaction Examples

### Submit a Compute Job

```javascript
const { ethers } = require("ethers");
const ComputeMarketplace = require("./artifacts/ComputeMarketplace.json");

// Connect to contract
const provider = new ethers.providers.JsonRpcProvider(process.env.QUBIC_RPC_URL);
const signer = new ethers.Wallet(process.env.PRIVATE_KEY, provider);
const marketplace = new ethers.Contract(
  CONTRACT_ADDRESS,
  ComputeMarketplace.abi,
  signer
);

// Submit job
const tx = await marketplace.submitJob(
  "medical-imaging-classification",
  "1000000000000000000", // 1 UC Token
  3, // verification nodes required
  "ipfs://QmJobSpecHash"
);

await tx.wait();
```

### Register as Compute Node

```javascript
const tx = await marketplace.registerNode(
  "0xNodeOperatorAddress",
  {
    cpu: 8,
    memory: "16GB",
    gpu: true,
    storage: "1TB"
  }
);

await tx.wait();
```

## Testing

```bash
# Run unit tests
npm run test

# Run integration tests
npm run test:integration

# Run coverage
npm run coverage
```

## Security Considerations

1. **Private Key Management**: Never commit private keys
2. **Access Control**: Implement proper role-based access
3. **Input Validation**: Always validate user inputs
4. **Reentrancy**: Use ReentrancyGuard for critical functions
5. **Gas Optimization**: Optimize for gas efficiency

## Auditing

All contracts should be audited before mainnet deployment:

1. Internal code review
2. Static analysis tools (Slither, Mythril)
3. External audit firm
4. Bug bounty program

## License

MIT License - see LICENSE file for details