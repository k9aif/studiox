# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
Object storage adapters.

Registered in ``ObjectStorageFactory``:

- ``local`` → LocalObjectStorageAdapter  (default: filesystem, zero-dep)
- ``s3``    → S3ObjectStorageAdapter      (OOB: S3 / MinIO via boto3)
- ``ibm``   → IbmCosObjectStorageAdapter  (IBM COS via ibm_boto3)
"""
