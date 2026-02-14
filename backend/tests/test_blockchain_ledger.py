"""
Full-scale test of the Blockchain Ledger implementation.
Tests all functionality: creation, hashing, signing, tamper detection,
queries, persistence, thread safety, and serialization.
"""
import sys
import os
import tempfile
import json
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.blockchain_ledger import BlockchainLedger, Block
from cryptography.hazmat.primitives import serialization


def run_tests():
    passed = 0
    failed = 0

    print("=" * 60)
    print("BLOCKCHAIN LEDGER FULL-SCALE TEST")
    print("=" * 60)

    # ---- TEST 1: Fresh initialization ----
    print("\n[TEST 1] Fresh initialization...")
    tmp = tempfile.mkdtemp()
    ledger = BlockchainLedger(storage_dir=tmp)
    assert len(ledger.chain) == 1, f"Expected 1 block, got {len(ledger.chain)}"
    assert ledger.chain[0].data["type"] == "genesis"
    assert ledger.chain[0].previous_hash == "0" * 64
    print("  PASS: Genesis block created correctly")
    passed += 1

    # ---- TEST 2: Hash computation determinism ----
    print("\n[TEST 2] Hash computation determinism...")
    genesis = ledger.chain[0]
    h1 = genesis.compute_hash()
    h2 = genesis.compute_hash()
    assert h1 == h2, "Hash not deterministic"
    assert h1 == genesis.block_hash, "Stored hash does not match computed"
    print(f"  PASS: Hash is deterministic: {h1[:24]}...")
    passed += 1

    # ---- TEST 3: Signature verification ----
    print("\n[TEST 3] RSA signature verification...")
    assert ledger.verify_block_signature(genesis), "Genesis signature invalid"
    print("  PASS: Genesis block signature verified")
    passed += 1

    # ---- TEST 4: Add verification blocks ----
    print("\n[TEST 4] Adding verification blocks...")
    b1 = ledger.add_verification_block(
        session_id="sess-001", user_id="user-A",
        verification_score=0.85, liveness_score=0.90,
        emotion_score=0.80, deepfake_score=0.75, passed=True,
        metadata={"test": True}
    )
    assert b1.index == 1
    assert b1.data["passed"] is True
    assert b1.data["scores"]["final"] == 0.85
    assert b1.previous_hash == genesis.block_hash
    print(f"  PASS: Block #1 added, hash={b1.block_hash[:24]}...")

    b2 = ledger.add_verification_block(
        session_id="sess-002", user_id="user-B",
        verification_score=0.55, liveness_score=0.50,
        emotion_score=0.60, deepfake_score=0.65, passed=False
    )
    assert b2.index == 2
    assert b2.data["passed"] is False
    assert b2.previous_hash == b1.block_hash
    print("  PASS: Block #2 added (failed verification)")
    passed += 1

    # ---- TEST 5: Add token block ----
    print("\n[TEST 5] Adding token block...")
    tb = ledger.add_token_block(
        session_id="sess-001", user_id="user-A",
        token_id="tok-XYZ", issued_at=1700000000.0,
        expires_at=1700000900.0, verification_score=0.85
    )
    assert tb.index == 3
    assert tb.data["type"] == "token_issuance"
    assert tb.data["token_id"] == "tok-XYZ"
    print("  PASS: Token block #3 added")
    passed += 1

    # ---- TEST 6: Chain integrity ----
    print("\n[TEST 6] Full chain integrity verification...")
    result = ledger.verify_chain_integrity()
    assert result["valid"] is True, f"Chain invalid: {result['errors']}"
    assert result["block_count"] == 4
    print(f"  PASS: Chain valid, {result['block_count']} blocks, 0 errors")
    passed += 1

    # ---- TEST 7: Single block verification ----
    print("\n[TEST 7] Single block verification...")
    for i in range(4):
        sv = ledger.verify_single_block(i)
        assert sv["valid"], f"Block #{i} invalid: {sv}"
    print("  PASS: All 4 blocks individually verified")
    passed += 1

    # ---- TEST 8: Tamper detection (data) ----
    print("\n[TEST 8a] Tamper detection (data modification)...")
    original_score = ledger.chain[1].data["scores"]["final"]
    ledger.chain[1].data["scores"]["final"] = 0.99
    tampered_result = ledger.verify_chain_integrity()
    assert tampered_result["valid"] is False, "Tampered chain should be invalid"
    assert any("hash mismatch" in e for e in tampered_result["errors"])
    ledger.chain[1].data["scores"]["final"] = original_score  # restore
    print("  PASS: Data tampering detected (hash mismatch)")

    print("[TEST 8b] Tamper detection (chain linkage)...")
    original_prev = ledger.chain[2].previous_hash
    ledger.chain[2].previous_hash = "aaaa" * 16
    tampered2 = ledger.verify_chain_integrity()
    assert tampered2["valid"] is False
    assert any("broken chain link" in e for e in tampered2["errors"])
    ledger.chain[2].previous_hash = original_prev  # restore
    print("  PASS: Chain linkage tampering detected")
    passed += 1

    # ---- TEST 9: Query methods ----
    print("\n[TEST 9] Query methods...")
    assert len(ledger.get_blocks_by_session("sess-001")) == 2
    assert len(ledger.get_blocks_by_user("user-B")) == 1
    assert ledger.get_block(0)["data"]["type"] == "genesis"
    assert ledger.get_block(99) is None
    assert len(ledger.get_latest_blocks(2)) == 2
    by_id = ledger.get_block_by_id(b1.block_id)
    assert by_id is not None
    assert by_id["index"] == 1
    print("  PASS: All query methods working")
    passed += 1

    # ---- TEST 10: Stats ----
    print("\n[TEST 10] Chain statistics...")
    stats = ledger.get_chain_stats()
    assert stats["total_blocks"] == 4
    assert stats["verification_blocks"] == 2
    assert stats["token_blocks"] == 1
    assert stats["verifications_passed"] == 1
    assert stats["verifications_failed"] == 1
    assert stats["pass_rate"] == 0.5
    print(f"  PASS: Stats correct - {stats['total_blocks']} blocks, pass_rate={stats['pass_rate']}")
    passed += 1

    # ---- TEST 11: Public key export ----
    print("\n[TEST 11] Public key export...")
    pem = ledger.get_public_key_pem()
    assert "-----BEGIN PUBLIC KEY-----" in pem
    assert "-----END PUBLIC KEY-----" in pem
    print(f"  PASS: Public key exported ({len(pem)} bytes)")
    passed += 1

    # ---- TEST 12: Proof generation ----
    print("\n[TEST 12] Standalone proof generation...")
    proof = ledger.generate_proof(1)
    assert proof is not None
    assert proof["proof_version"] == "1.0"
    assert proof["block"]["index"] == 1
    assert proof["previous_block_hash"] == genesis.block_hash
    assert "-----BEGIN PUBLIC KEY-----" in proof["public_key"]
    assert len(proof["verification_instructions"]) == 4
    proof_none = ledger.generate_proof(999)
    assert proof_none is None
    print("  PASS: Proof contains block, prev_hash, public_key, instructions")
    passed += 1

    # ---- TEST 13: Persistence (save & reload) ----
    print("\n[TEST 13] Persistence (save & reload)...")
    private_pem = ledger._private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    ledger2 = BlockchainLedger(
        private_key=private_pem,
        public_key=pem,
        storage_dir=tmp
    )
    assert len(ledger2.chain) == 4, f"Reload expected 4, got {len(ledger2.chain)}"
    reload_integrity = ledger2.verify_chain_integrity()
    assert reload_integrity["valid"], f"Reloaded chain invalid: {reload_integrity['errors']}"
    print(f"  PASS: Reloaded {len(ledger2.chain)} blocks, integrity verified")
    passed += 1

    # ---- TEST 14: Thread safety (concurrent writes) ----
    print("\n[TEST 14] Thread safety (concurrent writes)...")
    errors_found = []

    def add_block(idx):
        try:
            ledger.add_verification_block(
                session_id=f"concurrent-{idx}", user_id=f"user-{idx}",
                verification_score=0.7 + idx * 0.01, liveness_score=0.8,
                emotion_score=0.7, deepfake_score=0.6, passed=True
            )
        except Exception as e:
            errors_found.append(str(e))

    threads = [threading.Thread(target=add_block, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(errors_found) == 0, f"Thread errors: {errors_found}"
    indices = [b.index for b in ledger.chain]
    assert indices == list(range(len(ledger.chain))), f"Non-sequential: {indices}"
    final_check = ledger.verify_chain_integrity()
    assert final_check["valid"], f"Post-concurrent invalid: {final_check['errors']}"
    print(f"  PASS: 5 concurrent writes, chain valid with {final_check['block_count']} blocks")
    passed += 1

    # ---- TEST 15: Block serialization round-trip ----
    print("\n[TEST 15] Block serialization round-trip...")
    for b in ledger.chain:
        d = b.to_dict()
        restored = Block.from_dict(d)
        assert restored.block_hash == b.block_hash
        assert restored.compute_hash() == b.compute_hash()
        assert restored.signature == b.signature
    print(f"  PASS: All {len(ledger.chain)} blocks serialize/deserialize correctly")
    passed += 1

    # ---- TEST 16: Independent proof verification (simulated 3rd party) ----
    print("\n[TEST 16] Independent proof verification (3rd party simulation)...")
    proof = ledger.generate_proof(1)
    # Simulate a third party with only the proof JSON
    from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
    from cryptography.hazmat.primitives import hashes as crypto_hashes

    third_party_pubkey = serialization.load_pem_public_key(
        proof["public_key"].encode(), backend=None
    )
    block_data = proof["block"]
    # Recompute hash
    recomputed_block = Block.from_dict(block_data)
    computed_hash = recomputed_block.compute_hash()
    assert computed_hash == block_data["block_hash"], "3rd party hash mismatch"
    # Verify signature
    sig_bytes = bytes.fromhex(block_data["signature"])
    hash_bytes = block_data["block_hash"].encode()
    try:
        third_party_pubkey.verify(
            sig_bytes, hash_bytes,
            asym_padding.PSS(
                mgf=asym_padding.MGF1(crypto_hashes.SHA256()),
                salt_length=asym_padding.PSS.MAX_LENGTH,
            ),
            crypto_hashes.SHA256(),
        )
        sig_valid = True
    except Exception:
        sig_valid = False
    assert sig_valid, "3rd party signature verification failed"
    # Verify chain linkage
    assert block_data["previous_hash"] == proof["previous_block_hash"]
    print("  PASS: Third-party independently verified block hash + RSA signature + chain link")
    passed += 1

    # ---- TEST 17: Edge cases ----
    print("\n[TEST 17] Edge cases...")
    assert ledger.verify_single_block(-1) == {"valid": False, "error": "Block index out of range"}
    assert ledger.verify_single_block(9999) == {"valid": False, "error": "Block index out of range"}
    assert ledger.get_block_by_id("nonexistent") is None
    assert ledger.get_blocks_by_session("nonexistent") == []
    assert ledger.get_blocks_by_user("nonexistent") == []
    print("  PASS: All edge cases handled correctly")
    passed += 1

    # ---- TEST 18: Auto key persistence (no explicit keys) ----
    print("\n[TEST 18] Auto key persistence across restarts...")
    tmp2 = tempfile.mkdtemp()
    auto_ledger = BlockchainLedger(storage_dir=tmp2)  # No keys passed
    auto_ledger.add_verification_block(
        session_id="auto-001", user_id="user-auto",
        verification_score=0.92, liveness_score=0.95,
        emotion_score=0.85, deepfake_score=0.90, passed=True
    )
    auto_hash = auto_ledger.chain[-1].block_hash
    key_file = os.path.join(tmp2, "ledger_keys.json")
    assert os.path.exists(key_file), "Key file was not persisted"
    # Simulate restart — new instance with same storage dir, no explicit keys
    auto_ledger2 = BlockchainLedger(storage_dir=tmp2)
    assert len(auto_ledger2.chain) == 2, f"Expected 2 blocks, got {len(auto_ledger2.chain)}"
    assert auto_ledger2.chain[-1].block_hash == auto_hash
    auto_integrity = auto_ledger2.verify_chain_integrity()
    assert auto_integrity["valid"], f"Auto-reloaded chain invalid: {auto_integrity['errors']}"
    print(f"  PASS: Auto-persisted keys, chain survived restart with {len(auto_ledger2.chain)} blocks")
    passed += 1

    print("\n" + "=" * 60)
    print(f"ALL {passed} TESTS PASSED (0 failed)")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
