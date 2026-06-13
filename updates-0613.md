Also add setup.sh support to the same Studio scaffold template cleanup.

Additional required changes:

1. Add generated setup.sh to every exported scaffold.

Purpose:
A user should be able to unzip the scaffold and run:

  ./setup.sh
  ./run.sh

without manually fixing venv, framework path, PYTHONPATH, requirements, or .env.

2. setup.sh behavior

A. Python / venv detection

- Detect if already inside a Python virtual environment.
- If yes, continue.
- If not, ask:

  1) I will activate an existing venv myself
  2) Create .venv for me
- If option 2:

  - Prefer python3.12 if available
  - Then python3.11
  - Avoid python3.14 if possible because venv/ensurepip may fail
  - Create:

    .venv/
  - Print command for user to activate:

    source .venv/bin/activate
  - If the script cannot activate persistently because it is executed as a subprocess, clearly tell the user to run:

    source .venv/bin/activate
    ./setup.sh --continue

B. Framework setup

Ask:

1) Use existing k9-aif-framework folder
2) Clone k9-aif-framework into parent workspace

Expected default layout:

  workspace/
    customer_service_ai/
    k9-aif-framework/

If option 1:

- Prompt for framework path
- Accept absolute or relative path
- Validate folder exists
- Validate it contains:

  k9_aif_abb/

If option 2:

- Clone framework into:

  ../k9-aif-framework
- Use the configured GitHub URL for the framework.

C. Install dependencies

Run:

  python -m pip install --upgrade pip setuptools wheel

If requirements.txt exists:

  python -m pip install -r requirements.txt

If the framework has requirements.txt, install it too.

D. Update .env automatically

Ensure .env contains:

  K9_ENV=development
  K9_FRAMEWORK_PATH="../k9-aif-framework"

or the resolved user-provided path.

Do not duplicate keys.
Preserve unrelated existing .env values.

E. Validate imports

Run:

  python -c "import k9_aif_abb; print('k9_aif_abb import ok')"

Run a project-local import validation, with no k9_projects:

  python -c "from orchestrators.triage_orchestrator import TriageOrchestrator; print('project import ok')"

The actual orchestrator import should be generated dynamically based on the project’s generated orchestrator file.

F. Verification mode

Support:

  ./setup.sh --verify

This should check:

- Python version
- venv active
- .env exists
- K9_FRAMEWORK_PATH exists
- k9_aif_abb import works
- project-local imports work
- requirements installed enough to start

3. Update run.sh

run.sh should:

- Load .env safely.
- Resolve K9_FRAMEWORK_PATH relative to the project root if it is not absolute.
- Add project root and framework path to PYTHONPATH.
- Never require k9_projects.
- Print diagnostics:

  Python executable
  Python version
  Project root
  K9_FRAMEWORK_PATH
  PYTHONPATH
- Fail with clear messages if:

  - K9_FRAMEWORK_PATH is missing
  - k9_aif_abb cannot be imported
  - project-local imports fail

4. Update README.md

Add a Quick Start section:

  unzip customer_service_ai.zip
  cd customer_service_ai
  ./setup.sh
  source .venv/bin/activate
  ./run.sh

Also include the recommended workspace layout:

  workspace/
    customer_service_ai/
    k9-aif-framework/

But clearly state that k9_projects is not required.

Add troubleshooting for:

- ModuleNotFoundError: No module named 'k9_aif_abb'
- ModuleNotFoundError: No module named 'k9_projects'
- Wrong K9_FRAMEWORK_PATH
- Python 3.14 venv / ensurepip issue
- Missing virtual environment
- requirements.txt install failure

5. Regression test

Generate a scaffold into a temp directory without k9_projects.

Validate:

  grep -R "k9_projects" generated_project/

must return nothing.

Then run:

  ./setup.sh --verify
  ./run.sh

or at least validate imports using the same commands run.sh uses.


when .setup.sh is done successfully,  say setup was success

Ready to rumble!


Design rule:
The generated scaffold must be self-contained.
setup.sh and run.sh must support the exported project directly.
k9_projects was a legacy generator concept and must not appear in exported scaffolds.
