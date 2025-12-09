# Decentralized Healthcare AI Compute Platform

A specialized decentralized compute platform for healthcare AI workloads, built on the Ubuntu Patient Care infrastructure.

## 🎯 Mission

Enable privacy-preserving AI computation on medical data by connecting volunteer compute resources with researchers and developers worldwide.

## 🌟 Key Features

- **Healthcare-Optimized**: Native support for DICOM, FHIR, and medical imaging formats
- **Compliance-Ready**: Built-in POPIA/HIPAA compliance frameworks
- **Decentralized**: k-of-n redundancy and multi-node verification
- **Token-Based**: UC Token rewards for compute contributions
- **Developer-Friendly**: SDKs and tutorials for easy onboarding

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Researcher    │    │  Coordinator     │    │  Compute Nodes  │
│                 │◄──►│  (FastAPI)       │◄──►│  (Volunteer)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Dashboard │    │   Smart          │    │  Result Storage │
│   (React)       │    │   Contracts      │    │  (Cloudflare R2)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### For Researchers

```python
# Install SDK
pip install healthcare-compute

# Submit a medical image classification job
from healthcare_compute import Client

client = Client(api_key="your-api-key")
job = client.submit_job(
    type="medical-imaging",
    model="chest-xray-classifier",
    data_url="https://dataset-url/dicom-data.zip"
)

# Monitor progress
print(f"Job status: {job.status}")
results = job.get_results()
```

### For Compute Node Operators

```bash
# Register your node
curl -X POST https://api.healthcare-compute.org/nodes/register \
  -H "Content-Type: application/json" \
  -d '{"resources": {"cpu": 8, "memory": "16GB", "gpu": true}}'

# Run the worker agent
docker run -d --name healthcare-worker \
  healthcare-compute/worker:latest \
  --node-id YOUR_NODE_ID \
  --token YOUR_API_TOKEN
```

## 📊 Demo Workloads

1. **Chest X-ray Classification** (COVID-19 detection)
   - Dataset: COVIDx (publicly available)
   - Model: ResNet-50 trained on 50,000+ images

2. **Brain Tumor Segmentation**
   - Dataset: BraTS (publicly available)
   - Model: U-Net for 3D segmentation

3. **Drug Molecule Analysis**
   - Dataset: ChEMBL (public chemical database)
   - Model: Graph neural network for drug discovery

## 🛠️ Technology Stack

- **Backend**: Python 3.9+, FastAPI, PostgreSQL, Redis
- **Frontend**: React 18, TypeScript, Vite
- **Blockchain**: Qubic, Solidity smart contracts
- **Infrastructure**: Docker, Kubernetes, Render, Vercel
- **Storage**: Cloudflare R2, Supabase
- **Monitoring**: Prometheus, Grafana

## 📋 Roadmap

### Phase 1: MVP (Weeks 1-2)
- [x] Core smart contracts
- [x] Compute coordinator API
- [x] Basic worker agent
- [x] Public demo with COVIDx dataset

### Phase 2: Public Launch (Weeks 3-4)
- [ ] Web dashboard
- [ ] Node registration system
- [ ] UC Token rewards
- [ ] Documentation and tutorials

### Phase 3: Developer Onboarding (Weeks 5-6)
- [ ] Python/JavaScript SDKs
- [ ] Model marketplace
- [ ] Community Discord
- [ ] Hackathon preparation

### Phase 4: Research Integration (Weeks 7-8)
- [ ] Federated learning
- [ ] Advanced privacy features
- [ ] University partnerships
- [ ] Research grant program

## 🤝 Contributing

We welcome contributions! See our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/your-org/decentralized-healthcare-compute.git
cd decentralized-healthcare-compute

# Install dependencies
pip install -r requirements.txt
npm install

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Run locally
docker-compose up -d
npm run dev
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built on the [Ubuntu Patient Care](https://github.com/Ubuntu-Patient-Care) infrastructure
- Medical datasets provided by [COVIDx](https://github.com/lindawangg/COVID-Net) and [BraTS](https://www.med.upenn.edu/sbia/brats2020.html)
- Supported by the Qubic blockchain ecosystem

## 📞 Contact

- Discord: [Join our community](https://discord.gg/healthcare-compute)
- Twitter: [@HealthcareCompute](https://twitter.com/HealthcareCompute)
- Email: team@healthcare-compute.org

---

⚠️ **Important**: This platform currently uses only public, anonymized medical datasets for demonstration purposes. No private patient data is processed.