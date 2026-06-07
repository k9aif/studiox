# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9-AIF ASCII Mascot Utilities
Central place for ASCII dog logos and success/failure messages.
"""

DOG_HAPPY = r"""
   / \__
  ( ^   @\___
  /         O
 /   (_____/
/_____/   U
"""

DOG_ANGRY = r"""
   / \__
  ( >   @\___
  /    ---O
 /   (_____/
/_____/   V
"""

def print_success(context: str = "Operation"):
    print("Woof!")
    print(DOG_HAPPY)
    print(f"[K9-AIF] {context} completed successfully!")
    print("[READY TO RUMBLE!] \n")

def print_failure(context: str = "Operation"):
    print(DOG_ANGRY)
    print(f"[K9-AIF] {context} found issues! Please check above logs.")
    print("Grrrr... \n")