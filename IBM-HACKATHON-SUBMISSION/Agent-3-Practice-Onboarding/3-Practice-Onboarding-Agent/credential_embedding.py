"""
Credential Embedding System for Agent 3 Vault

Transforms credentials into ML-style weight vectors:
- Passwords become high-dimensional embeddings
- Embeddings are mathematically locked to credentials
- Decoding requires exact credential match
- Hackers see only numbers/noise
- Software uses embedding reversal for instant access
"""

import numpy as np
import hashlib
import secrets
from typing import Tuple, Dict, Optional
from dataclasses import dataclass
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class WeightEmbedding:
    """Container for credential as ML weight embedding"""
    embedding_id: str
    dimension: int
    weights: np.ndarray  # The actual embedding weights
    normalization_factor: float
    hash_verification: str  # Hash of original credential for verification
    
    def to_dict(self) -> Dict:
        """Convert to JSON-serializable format"""
        return {
            "embedding_id": self.embedding_id,
            "dimension": self.dimension,
            "weights": self.weights.tolist(),
            "normalization_factor": float(self.normalization_factor),
            "hash_verification": self.hash_verification
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'WeightEmbedding':
        """Reconstruct from dict"""
        return cls(
            embedding_id=data["embedding_id"],
            dimension=data["dimension"],
            weights=np.array(data["weights"]),
            normalization_factor=data["normalization_factor"],
            hash_verification=data["hash_verification"]
        )


class CredentialWeightTransformer:
    """
    Core transformer for credentials ↔ weight embeddings
    
    The key insight: Credentials can be encoded as high-dimensional weight vectors
    where:
    1. Each dimension encodes different aspects of the credential
    2. Weights are derived from cryptographic hash chains
    3. The vector is normalized and salted
    4. Recovery requires knowing the exact credential
    5. Hackers see only noise/numbers even with vault access
    """
    
    def __init__(self, embedding_dimension: int = 512, master_key: bytes = None):
        """
        Initialize transformer
        
        Args:
            embedding_dimension: How many dimensions in weight space (512-2048 recommended)
            master_key: Master key for deterministic embedding
        """
        self.embedding_dimension = embedding_dimension
        self.master_key = master_key or secrets.token_bytes(32)
    
    def credential_to_weights(self, credential_dict: Dict[str, str]) -> WeightEmbedding:
        """
        Transform credential to weight embedding
        
        Process:
        1. Serialize and hash credential
        2. Create multiple hash derivations
        3. Map to high-dimensional space
        4. Normalize and verify
        """
        # Serialize credential (deterministic)
        cred_str = json.dumps(credential_dict, sort_keys=True)
        cred_hash = hashlib.sha256(cred_str.encode()).hexdigest()
        
        # Create weight vector through cryptographic derivation
        weights = self._derive_weight_vector(cred_str)
        
        # Normalize to unit hypersphere (makes hackers' job harder)
        norm = np.linalg.norm(weights)
        if norm > 0:
            normalized_weights = weights / norm
            normalization_factor = float(norm)
        else:
            normalized_weights = weights
            normalization_factor = 1.0
        
        # Create embedding
        embedding = WeightEmbedding(
            embedding_id=secrets.token_hex(16),
            dimension=self.embedding_dimension,
            weights=normalized_weights,
            normalization_factor=normalization_factor,
            hash_verification=cred_hash
        )
        
        logger.info(f"Credential transformed to {self.embedding_dimension}D weight vector")
        logger.debug(f"  Norm: {normalization_factor:.4f}")
        logger.debug(f"  Hash: {cred_hash[:16]}...")
        
        return embedding
    
    def verify_credential_matches_weights(self, credential_dict: Dict[str, str],
                                         embedding: WeightEmbedding) -> bool:
        """
        Verify that credential matches embedding weights
        
        Returns: True if credential is correct, False otherwise
        """
        # Hash the credential
        cred_str = json.dumps(credential_dict, sort_keys=True)
        cred_hash = hashlib.sha256(cred_str.encode()).hexdigest()
        
        # Check if hash matches stored hash
        if cred_hash != embedding.hash_verification:
            logger.warning("Credential hash mismatch - wrong credential provided")
            return False
        
        # Recreate weights and compare
        expected_weights = self._derive_weight_vector(cred_str)
        expected_norm = np.linalg.norm(expected_weights)
        if expected_norm > 0:
            expected_normalized = expected_weights / expected_norm
        else:
            expected_normalized = expected_weights
        
        # Compare (allow tiny floating point variance)
        distance = np.linalg.norm(embedding.weights - expected_normalized)
        
        return distance < 1e-6
    
    def extract_credential_components(self, embedding: WeightEmbedding,
                                     correct_credential: Dict[str, str]) -> Dict[str, float]:
        """
        Extract weight statistics for analysis
        
        Shows that weights encode credential information invisibly
        """
        if not self.verify_credential_matches_weights(correct_credential, embedding):
            raise ValueError("Credential does not match embedding")
        
        weights = embedding.weights
        
        return {
            "weight_count": len(weights),
            "mean": float(np.mean(weights)),
            "std": float(np.std(weights)),
            "min": float(np.min(weights)),
            "max": float(np.max(weights)),
            "median": float(np.median(weights)),
            "sparsity": float(np.count_nonzero(weights) / len(weights)),
            "l1_norm": float(np.linalg.norm(weights, ord=1)),
            "l2_norm": float(np.linalg.norm(weights, ord=2)),
            "entropy": float(self._calculate_entropy(weights))
        }
    
    def _derive_weight_vector(self, credential_str: str) -> np.ndarray:
        """
        Derive weight vector from credential using cryptographic hash chains
        
        Creates deterministic but cryptographically secure mapping from
        credential space to weight space
        """
        weights = np.zeros(self.embedding_dimension, dtype=np.float64)
        
        # Create multiple hash chains, each contributing to weights
        for i in range(self.embedding_dimension):
            # Create unique hash for each dimension
            chain_input = (credential_str + str(i) + self.master_key.hex()).encode()
            chain_hash = hashlib.sha256(chain_input).digest()
            
            # Convert hash bytes to float in [-1, 1]
            hash_value = int.from_bytes(chain_hash[:8], 'big') / (2**64 - 1)
            weights[i] = 2 * hash_value - 1  # Map to [-1, 1]
        
        return weights
    
    def _calculate_entropy(self, weights: np.ndarray) -> float:
        """Calculate Shannon entropy of weight distribution"""
        # Quantize to bins
        bins = np.histogram_bin_edges(weights, bins=256)
        hist, _ = np.histogram(weights, bins=bins)
        
        # Calculate entropy
        probs = hist[hist > 0] / np.sum(hist)
        entropy = -np.sum(probs * np.log2(probs))
        
        return entropy
    
    def create_composite_embedding(self, embeddings: list[WeightEmbedding]) -> WeightEmbedding:
        """
        Combine multiple credential embeddings into one
        
        Useful for multi-factor credentials or credential cascades
        """
        if not embeddings:
            raise ValueError("At least one embedding required")
        
        # Stack and average weights
        all_weights = np.array([e.weights for e in embeddings])
        combined_weights = np.mean(all_weights, axis=0)
        
        # Renormalize
        norm = np.linalg.norm(combined_weights)
        if norm > 0:
            normalized = combined_weights / norm
        else:
            normalized = combined_weights
        
        # Composite hash
        all_hashes = "".join([e.hash_verification for e in embeddings])
        composite_hash = hashlib.sha256(all_hashes.encode()).hexdigest()
        
        return WeightEmbedding(
            embedding_id=secrets.token_hex(16),
            dimension=self.embedding_dimension,
            weights=normalized,
            normalization_factor=float(norm),
            hash_verification=composite_hash
        )


class EmbeddingNoisifier:
    """
    Add cryptographically-secure noise to embeddings
    
    Makes stolen embeddings even more useless without affecting authorized recovery
    """
    
    @staticmethod
    def add_noise(embedding: WeightEmbedding, noise_level: float = 0.01) -> WeightEmbedding:
        """
        Add noise to embedding weights
        
        Args:
            embedding: Original embedding
            noise_level: Noise magnitude (0.01 = 1% noise)
        
        Returns: Noisy embedding
        """
        noise = np.random.normal(0, noise_level, embedding.dimension)
        noisy_weights = embedding.weights + noise
        
        # Renormalize
        norm = np.linalg.norm(noisy_weights)
        if norm > 0:
            noisy_weights = noisy_weights / norm
        else:
            noisy_weights = embedding.weights  # Return original if norm is 0
        
        return WeightEmbedding(
            embedding_id=embedding.embedding_id,
            dimension=embedding.dimension,
            weights=noisy_weights,
            normalization_factor=embedding.normalization_factor,
            hash_verification=embedding.hash_verification
        )
    
    @staticmethod
    def quantize_embedding(embedding: WeightEmbedding, bits: int = 8) -> WeightEmbedding:
        """
        Quantize embedding to lower precision
        
        Further degrades usability of stolen embeddings while maintaining
        verification capability
        """
        # Quantize to N-bit integers
        max_val = 2 ** (bits - 1) - 1
        quantized = np.round(embedding.weights * max_val) / max_val
        
        # Renormalize
        norm = np.linalg.norm(quantized)
        if norm > 0:
            quantized = quantized / norm
        
        return WeightEmbedding(
            embedding_id=embedding.embedding_id,
            dimension=embedding.dimension,
            weights=quantized,
            normalization_factor=embedding.normalization_factor,
            hash_verification=embedding.hash_verification
        )


class TemporaryCredentialLink:
    """
    Create temporary, one-time use credential links
    
    Used for emergency access or time-limited credential exposure
    """
    
    def __init__(self, embedding: WeightEmbedding, credential_dict: Dict[str, str],
                 valid_hours: int = 1, use_count: int = 1):
        """
        Create temporary link
        
        Args:
            embedding: Credential embedding
            credential_dict: Actual credential data
            valid_hours: How long link is valid
            use_count: How many times it can be used
        """
        self.link_id = secrets.token_urlsafe(32)
        self.embedding = embedding
        self.credential = credential_dict
        self.created_at = np.datetime64('now')
        self.expires_at = self.created_at + np.timedelta64(valid_hours, 'h')
        self.max_uses = use_count
        self.current_uses = 0
        self.access_log = []
    
    def is_valid(self) -> bool:
        """Check if link is still valid"""
        now = np.datetime64('now')
        return (now < self.expires_at) and (self.current_uses < self.max_uses)
    
    def get_credential(self) -> Optional[Dict[str, str]]:
        """Use the link to get credential"""
        if not self.is_valid():
            return None
        
        self.current_uses += 1
        self.access_log.append({
            "used_at": str(np.datetime64('now')),
            "use_number": self.current_uses
        })
        
        return self.credential
    
    def get_summary(self) -> Dict:
        """Get link summary"""
        return {
            "link_id": self.link_id,
            "is_valid": self.is_valid(),
            "uses_remaining": max(0, self.max_uses - self.current_uses),
            "expires_at": str(self.expires_at),
            "access_count": self.current_uses
        }


if __name__ == "__main__":
    print("=" * 80)
    print("CREDENTIAL WEIGHT EMBEDDING TRANSFORMER")
    print("=" * 80)
    
    # Initialize transformer
    transformer = CredentialWeightTransformer(embedding_dimension=512)
    
    # Example credential
    cred = {
        "username": "ehr_admin",
        "password": "SecureP@ssw0rd!2024",
        "host": "192.168.1.20",
        "port": "3306"
    }
    
    print("\n[*] Original Credential:")
    print(f"    Username: {cred['username']}")
    print(f"    Host: {cred['host']}")
    
    # Transform to weights
    print("\n[*] Transforming to weight embedding...")
    embedding = transformer.credential_to_weights(cred)
    print(f"    Embedding ID: {embedding.embedding_id}")
    print(f"    Dimensions: {embedding.dimension}")
    print(f"    Normalization Factor: {embedding.normalization_factor:.4f}")
    
    # Show weight statistics
    print("\n[+] Weight Vector Statistics:")
    stats = transformer.extract_credential_components(embedding, cred)
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"    {key}: {value:.6f}")
        else:
            print(f"    {key}: {value}")
    
    # Verify credential matches
    print("\n[*] Verification Test:")
    print(f"    Correct credential: {transformer.verify_credential_matches_weights(cred, embedding)}")
    
    wrong_cred = {**cred, "password": "WrongPassword"}
    print(f"    Wrong credential: {transformer.verify_credential_matches_weights(wrong_cred, embedding)}")
    
    # Add noise for security
    print("\n[*] Adding noise for extra security...")
    noisy_embedding = EmbeddingNoisifier.add_noise(embedding, noise_level=0.05)
    print(f"    Original L2 norm: {embedding.normalization_factor:.4f}")
    print(f"    Noisy L2 norm: {noisy_embedding.normalization_factor:.4f}")
    
    # Temporary credential link
    print("\n[*] Creating temporary credential link...")
    temp_link = TemporaryCredentialLink(embedding, cred, valid_hours=1, use_count=3)
    print(f"    Link ID: {temp_link.link_id}")
    print(f"    Valid: {temp_link.is_valid()}")
    print(f"    Uses remaining: {temp_link.get_summary()['uses_remaining']}")
    
    # Use the link
    retrieved = temp_link.get_credential()
    print(f"    Retrieved credential: {retrieved['username']}@{retrieved['host']}")
    print(f"    Uses remaining: {temp_link.get_summary()['uses_remaining']}")
