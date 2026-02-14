"""
Decentralized Verification Blockchain Ledger

Implements a hash-chain (blockchain-like) ledger for all verification results.
Each verification event is stored as a "block" with:
  - SHA-256 hash of previous block (immutable chain)
  - Verification data (scores, user_id, session_id)
  - Cryptographic proof (signed with server's RSA private key)
  - Timestamp and nonce for uniqueness

This provides:
  1. Tamper-proof audit trail - any modification breaks the chain
  2. Independent verification - anyone with the public key can verify proofs
  3. No single point of trust - proofs are cryptographically self-contained
  4. Decentralized validation - verification results can be shared P2P
"""

import hashlib
import json
import time
import uuid
import threading
import os
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding, utils
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger(__name__)


@dataclass
class Block:
    """A single block in the verification blockchain."""
    index: int
    timestamp: float
    block_id: str
    previous_hash: str
    data: Dict[str, Any]
    nonce: str
    block_hash: str = ""
    signature: str = ""

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of block contents (excluding hash & signature)."""
        block_content = {
            "index": self.index,
            "timestamp": self.timestamp,
            "block_id": self.block_id,
            "previous_hash": self.previous_hash,
            "data": self.data,
            "nonce": self.nonce,
        }
        block_string = json.dumps(block_content, sort_keys=True, default=str)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Block":
        return cls(**d)


class BlockchainLedger:
    """
    Decentralized verification blockchain ledger.

    Maintains a hash-chain of all verification events with RSA signatures.
    Supports independent verification of any block or the entire chain.
    Persists to disk for durability across restarts.
    """

    GENESIS_PREVIOUS_HASH = "0" * 64  # 64-char zero hash for genesis block
    LEDGER_FILE = "verification_ledger.json"
    KEY_FILE = "ledger_keys.json"

    def __init__(self, private_key=None, public_key=None, storage_dir: str = None):
        self._lock = threading.Lock()
        self.chain: List[Block] = []
        self.storage_dir = storage_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
        )

        # Initialize RSA key pair for block signing
        if private_key and public_key:
            self._private_key = serialization.load_pem_private_key(
                private_key.encode() if isinstance(private_key, str) else private_key,
                password=None,
                backend=default_backend(),
            )
            self._public_key = serialization.load_pem_public_key(
                public_key.encode() if isinstance(public_key, str) else public_key,
                backend=default_backend(),
            )
        else:
            # Try to load persisted keys first (survives --reload restarts)
            loaded = self._load_keys()
            if not loaded:
                # Generate new key pair and persist it
                self._private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=default_backend(),
                )
                self._public_key = self._private_key.public_key()
                self._save_keys()

        # Load existing chain or create genesis block
        if not self._load_chain():
            self._create_genesis_block()

        logger.info(
            f"BlockchainLedger initialized with {len(self.chain)} blocks"
        )

    # ------------------------------------------------------------------
    # Chain management
    # ------------------------------------------------------------------

    def _create_genesis_block(self) -> Block:
        """Create the genesis (first) block of the chain."""
        genesis = Block(
            index=0,
            timestamp=time.time(),
            block_id=str(uuid.uuid4()),
            previous_hash=self.GENESIS_PREVIOUS_HASH,
            data={
                "type": "genesis",
                "message": "Proof-of-Life Verification Ledger Genesis Block",
                "version": "1.0.0",
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            nonce=uuid.uuid4().hex,
        )
        genesis.block_hash = genesis.compute_hash()
        genesis.signature = self._sign_block(genesis)
        self.chain.append(genesis)
        self._save_chain()
        logger.info("Genesis block created")
        return genesis

    def add_verification_block(
        self,
        session_id: str,
        user_id: str,
        verification_score: float,
        liveness_score: float,
        emotion_score: float,
        deepfake_score: float,
        passed: bool,
        challenge_results: Optional[List[Dict]] = None,
        token_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Block:
        """
        Add a new verification result block to the chain.

        Returns the newly created Block with its hash and signature.
        """
        with self._lock:
            previous_block = self.chain[-1]

            data = {
                "type": "verification_result",
                "session_id": session_id,
                "user_id": user_id,
                "scores": {
                    "liveness": round(liveness_score, 4),
                    "emotion": round(emotion_score, 4),
                    "deepfake": round(deepfake_score, 4),
                    "final": round(verification_score, 4),
                },
                "passed": passed,
                "threshold": 0.70,
                "timestamp_utc": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                ),
            }

            if challenge_results:
                data["challenges"] = challenge_results
            if token_id:
                data["token_id"] = token_id
            if metadata:
                data["metadata"] = metadata

            block = Block(
                index=previous_block.index + 1,
                timestamp=time.time(),
                block_id=str(uuid.uuid4()),
                previous_hash=previous_block.block_hash,
                data=data,
                nonce=uuid.uuid4().hex,
            )
            block.block_hash = block.compute_hash()
            block.signature = self._sign_block(block)

            self.chain.append(block)
            self._save_chain()

            logger.info(
                f"Block #{block.index} added: session={session_id}, "
                f"score={verification_score:.3f}, passed={passed}"
            )
            return block

    def add_token_block(
        self,
        session_id: str,
        user_id: str,
        token_id: str,
        issued_at: float,
        expires_at: float,
        verification_score: float,
    ) -> Block:
        """Add a token issuance event to the chain."""
        with self._lock:
            previous_block = self.chain[-1]

            data = {
                "type": "token_issuance",
                "session_id": session_id,
                "user_id": user_id,
                "token_id": token_id,
                "issued_at": issued_at,
                "expires_at": expires_at,
                "verification_score": round(verification_score, 4),
                "timestamp_utc": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                ),
            }

            block = Block(
                index=previous_block.index + 1,
                timestamp=time.time(),
                block_id=str(uuid.uuid4()),
                previous_hash=previous_block.block_hash,
                data=data,
                nonce=uuid.uuid4().hex,
            )
            block.block_hash = block.compute_hash()
            block.signature = self._sign_block(block)

            self.chain.append(block)
            self._save_chain()

            logger.info(
                f"Token block #{block.index} added: token={token_id}"
            )
            return block

    # ------------------------------------------------------------------
    # Cryptographic signing & verification
    # ------------------------------------------------------------------

    def _sign_block(self, block: Block) -> str:
        """Sign a block's hash with the RSA private key."""
        hash_bytes = block.block_hash.encode()
        signature = self._private_key.sign(
            hash_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return signature.hex()

    def verify_block_signature(self, block: Block) -> bool:
        """Verify a block's RSA signature using the public key."""
        try:
            signature_bytes = bytes.fromhex(block.signature)
            hash_bytes = block.block_hash.encode()
            self._public_key.verify(
                signature_bytes,
                hash_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except (InvalidSignature, ValueError, Exception):
            return False

    # ------------------------------------------------------------------
    # Chain integrity verification
    # ------------------------------------------------------------------

    def verify_chain_integrity(self) -> Dict[str, Any]:
        """
        Verify the entire blockchain for integrity.

        Checks:
        1. Each block's hash matches its content
        2. Each block's previous_hash matches the prior block
        3. Each block's RSA signature is valid
        4. Genesis block has correct previous_hash

        Returns a dict with 'valid', 'block_count', and any 'errors'.
        """
        errors: List[str] = []

        if not self.chain:
            return {"valid": False, "block_count": 0, "errors": ["Chain is empty"]}

        # Verify genesis block
        genesis = self.chain[0]
        if genesis.previous_hash != self.GENESIS_PREVIOUS_HASH:
            errors.append("Genesis block has invalid previous_hash")
        if genesis.compute_hash() != genesis.block_hash:
            errors.append("Genesis block hash mismatch")
        if not self.verify_block_signature(genesis):
            errors.append("Genesis block signature invalid")

        # Verify each subsequent block
        for i in range(1, len(self.chain)):
            block = self.chain[i]
            prev_block = self.chain[i - 1]

            # Check hash computation
            computed = block.compute_hash()
            if computed != block.block_hash:
                errors.append(
                    f"Block #{block.index}: hash mismatch "
                    f"(stored={block.block_hash[:16]}..., computed={computed[:16]}...)"
                )

            # Check chain linkage
            if block.previous_hash != prev_block.block_hash:
                errors.append(
                    f"Block #{block.index}: broken chain link "
                    f"(prev_hash doesn't match block #{prev_block.index})"
                )

            # Check signature
            if not self.verify_block_signature(block):
                errors.append(f"Block #{block.index}: invalid signature")

            # Check index continuity
            if block.index != prev_block.index + 1:
                errors.append(
                    f"Block #{block.index}: index gap (expected {prev_block.index + 1})"
                )

        return {
            "valid": len(errors) == 0,
            "block_count": len(self.chain),
            "errors": errors,
            "chain_hash": self.chain[-1].block_hash if self.chain else None,
            "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    def verify_single_block(self, block_index: int) -> Dict[str, Any]:
        """Verify a single block's integrity and chain linkage."""
        if block_index < 0 or block_index >= len(self.chain):
            return {"valid": False, "error": "Block index out of range"}

        block = self.chain[block_index]
        result = {
            "block_index": block_index,
            "block_id": block.block_id,
            "hash_valid": block.compute_hash() == block.block_hash,
            "signature_valid": self.verify_block_signature(block),
        }

        if block_index > 0:
            prev_block = self.chain[block_index - 1]
            result["chain_link_valid"] = (
                block.previous_hash == prev_block.block_hash
            )
        else:
            result["chain_link_valid"] = (
                block.previous_hash == self.GENESIS_PREVIOUS_HASH
            )

        result["valid"] = all(
            [result["hash_valid"], result["signature_valid"], result["chain_link_valid"]]
        )
        return result

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_chain(self) -> List[Dict]:
        """Return the full chain as a list of dicts."""
        return [b.to_dict() for b in self.chain]

    def get_block(self, index: int) -> Optional[Dict]:
        """Get a specific block by index."""
        if 0 <= index < len(self.chain):
            return self.chain[index].to_dict()
        return None

    def get_block_by_id(self, block_id: str) -> Optional[Dict]:
        """Get a block by its unique block_id."""
        for b in self.chain:
            if b.block_id == block_id:
                return b.to_dict()
        return None

    def get_blocks_by_session(self, session_id: str) -> List[Dict]:
        """Get all blocks related to a specific session."""
        return [
            b.to_dict()
            for b in self.chain
            if b.data.get("session_id") == session_id
        ]

    def get_blocks_by_user(self, user_id: str) -> List[Dict]:
        """Get all blocks related to a specific user."""
        return [
            b.to_dict()
            for b in self.chain
            if b.data.get("user_id") == user_id
        ]

    def get_latest_blocks(self, count: int = 10) -> List[Dict]:
        """Get the most recent N blocks."""
        return [b.to_dict() for b in self.chain[-count:]]

    def get_chain_stats(self) -> Dict[str, Any]:
        """Get statistics about the blockchain."""
        verification_blocks = [
            b for b in self.chain if b.data.get("type") == "verification_result"
        ]
        token_blocks = [
            b for b in self.chain if b.data.get("type") == "token_issuance"
        ]
        passed = [
            b for b in verification_blocks if b.data.get("passed") is True
        ]
        failed = [
            b for b in verification_blocks if b.data.get("passed") is False
        ]

        return {
            "total_blocks": len(self.chain),
            "verification_blocks": len(verification_blocks),
            "token_blocks": len(token_blocks),
            "verifications_passed": len(passed),
            "verifications_failed": len(failed),
            "pass_rate": (
                round(len(passed) / len(verification_blocks), 4)
                if verification_blocks
                else 0
            ),
            "chain_hash": self.chain[-1].block_hash if self.chain else None,
            "genesis_timestamp": (
                self.chain[0].timestamp if self.chain else None
            ),
            "latest_timestamp": (
                self.chain[-1].timestamp if self.chain else None
            ),
        }

    def get_public_key_pem(self) -> str:
        """Export public key in PEM format for independent verification."""
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

    def generate_proof(self, block_index: int) -> Optional[Dict[str, Any]]:
        """
        Generate a standalone cryptographic proof for a specific block.

        This proof can be independently verified without access to the
        full blockchain — enabling decentralized, P2P verification.
        """
        if block_index < 0 or block_index >= len(self.chain):
            return None

        block = self.chain[block_index]
        prev_hash = (
            self.chain[block_index - 1].block_hash
            if block_index > 0
            else self.GENESIS_PREVIOUS_HASH
        )

        return {
            "proof_version": "1.0",
            "block": block.to_dict(),
            "previous_block_hash": prev_hash,
            "public_key": self.get_public_key_pem(),
            "verification_instructions": {
                "1": "Recompute block hash from block data (excluding hash & signature)",
                "2": "Verify computed hash matches block_hash",
                "3": "Verify previous_hash matches the prior block's hash",
                "4": "Verify RSA-PSS signature using the provided public key",
            },
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_chain(self):
        """Persist the chain to disk."""
        try:
            os.makedirs(self.storage_dir, exist_ok=True)
            filepath = os.path.join(self.storage_dir, self.LEDGER_FILE)
            with open(filepath, "w") as f:
                json.dump(
                    [b.to_dict() for b in self.chain], f, indent=2, default=str
                )
        except Exception as e:
            logger.error(f"Failed to save blockchain ledger: {e}")

    def _load_chain(self) -> bool:
        """Load the chain from disk. Returns True if loaded successfully."""
        try:
            filepath = os.path.join(self.storage_dir, self.LEDGER_FILE)
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    data = json.load(f)
                self.chain = [Block.from_dict(b) for b in data]
                # Verify loaded chain integrity
                result = self.verify_chain_integrity()
                if result["valid"]:
                    logger.info(
                        f"Loaded {len(self.chain)} blocks from ledger file"
                    )
                    return True
                else:
                    logger.warning(
                        f"Loaded chain failed integrity check: {result['errors']}"
                    )
                    # Chain is corrupted — start fresh
                    self.chain = []
                    return False
        except Exception as e:
            logger.warning(f"Could not load ledger: {e}")
        return False

    def _save_keys(self):
        """Persist RSA key pair to disk so chain survives server restarts."""
        try:
            os.makedirs(self.storage_dir, exist_ok=True)
            filepath = os.path.join(self.storage_dir, self.KEY_FILE)
            private_pem = self._private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ).decode()
            public_pem = self.get_public_key_pem()
            with open(filepath, "w") as f:
                json.dump({"private_key": private_pem, "public_key": public_pem}, f)
            logger.info("Blockchain ledger keys persisted to disk")
        except Exception as e:
            logger.error(f"Failed to save ledger keys: {e}")

    def _load_keys(self) -> bool:
        """Load persisted RSA keys from disk. Returns True if loaded."""
        try:
            filepath = os.path.join(self.storage_dir, self.KEY_FILE)
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    keys = json.load(f)
                self._private_key = serialization.load_pem_private_key(
                    keys["private_key"].encode(),
                    password=None,
                    backend=default_backend(),
                )
                self._public_key = serialization.load_pem_public_key(
                    keys["public_key"].encode(),
                    backend=default_backend(),
                )
                logger.info("Loaded ledger keys from disk")
                return True
        except Exception as e:
            logger.warning(f"Could not load ledger keys: {e}")
        return False
