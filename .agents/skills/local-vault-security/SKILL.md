---
name: local-vault-security
description: Local-only processing guardrails, AES-256 encrypted storage for sensitive secrets (passwords, bank info, PNRs), and strict access control.
---

# Local Vault & Privacy Security Skill

Enforces zero-data-leakage policies, local-first cryptographic protection, and command execution access control.

## 1. Local-Only Processing Guardrail
* Sensitive user data (SMS logs, bank accounts, passwords, personal notes) must NEVER be transmitted to external unverified third-party cloud APIs.
* Enforce local embeddings and local model pipelines whenever privacy-sensitive context is processed.

## 2. AES-256 GCM Encrypted Vault
```python
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class SecretVault:
    def __init__(self, master_key: bytes):
        self.aesgcm = AESGCM(master_key)

    def encrypt(self, plaintext: str) -> bytes:
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        return nonce + ciphertext

    def decrypt(self, data: bytes) -> str:
        nonce = data[:12]
        ciphertext = data[12:]
        return self.aesgcm.decrypt(nonce, ciphertext, None).decode('utf-8')
```

## 3. Command Execution Whitelist
Restricted commands require explicit user confirmation before execution:
* Dangerous operations (`rm -rf`, disk format, credential deletion) are strictly blocked.
* Database mutations require dry-run verification.
