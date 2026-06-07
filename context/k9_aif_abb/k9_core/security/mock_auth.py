# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

class MockAuth:
    def __init__(self, secret: str = "demo-secret", **kwargs):
        self.secret = secret
    def authenticate(self, token: str) -> bool:
        return token == "demo-secret"