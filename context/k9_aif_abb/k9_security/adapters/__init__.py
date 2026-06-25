# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
k9_security.adapters — Secret manager adapter implementations.

Available adapters::

    env    → EnvSecretAdapter    (default — reads os.environ)
    vault  → VaultSecretAdapter  (HashiCorp Vault via VAULT_ADDR + VAULT_TOKEN)
    aws    → AwsSecretAdapter    (AWS Secrets Manager via boto3)
    ibm    → IbmSecretAdapter    (IBM Secrets Manager via ibm-platform-services)

Typical import::

    from k9_aif_abb.k9_security.adapters.env_adapter import EnvSecretAdapter
"""

from k9_aif_abb.k9_security.adapters.env_adapter import EnvSecretAdapter
from k9_aif_abb.k9_security.adapters.vault_adapter import VaultSecretAdapter
from k9_aif_abb.k9_security.adapters.aws_adapter import AwsSecretAdapter
from k9_aif_abb.k9_security.adapters.ibm_adapter import IbmSecretAdapter

__all__ = [
    "EnvSecretAdapter",
    "VaultSecretAdapter",
    "AwsSecretAdapter",
    "IbmSecretAdapter",
]
