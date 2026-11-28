# Sync Python Dependencies

Detect and fix version mismatches between `pyproject.toml` and `requirements.txt` 
that cause hermetic build failures.

## When to Use

Use this skill when:
- Hermetic builds fail with "Could not find a version that satisfies the requirement"
- Renovate/Dependabot updated lock files but not source files
- You see version mismatches between `pyproject.toml` and `requirements.txt`
- After manually updating dependencies in `pyproject.toml`

## What It Does

1. **Analyzes** `pyproject.toml` and `requirements.txt` for version mismatches
2. **Reports** which packages have different versions in each file
3. **Explains** why the mismatch causes hermetic build failures
4. **Fixes** by synchronizing versions and regenerating lock files
5. **Verifies** the fix resolves the issue

## How It Works

### Step 1: Detect Version Mismatches

```bash
# Extract package versions from pyproject.toml
echo "=== Checking for version mismatches ==="
echo ""

# Parse dependencies from pyproject.toml
PYPROJECT_DEPS=$(python3 -c "
import tomllib
with open('pyproject.toml', 'rb') as f:
    data = tomllib.load(f)
deps = data.get('project', {}).get('dependencies', [])
for dep in deps:
    if '==' in dep:
        pkg, ver = dep.split('==')
        print(f'{pkg.strip()}=={ver.strip()}')
" 2>/dev/null || echo "Failed to parse pyproject.toml")

echo "Dependencies in pyproject.toml:"
echo "$PYPROJECT_DEPS"
echo ""

# Parse dependencies from requirements.txt
echo "Dependencies in requirements.txt:"
grep -E "^[a-zA-Z0-9_-]+==.*\\" requirements.txt | sed 's/ \\$//' | head -20
echo ""

# Find mismatches
echo "=== Analyzing mismatches ==="
python3 <<'PYEOF'
import tomllib
import re

# Read pyproject.toml
with open('pyproject.toml', 'rb') as f:
    pyproject = tomllib.load(f)
    
pyproject_deps = {}
for dep in pyproject.get('project', {}).get('dependencies', []):
    if '==' in dep:
        # Handle both "pkg==ver" and "pkg >= ver" formats
        parts = dep.split('==')
        pkg = parts[0].strip().strip('"').strip("'")
        ver = parts[1].strip().strip('"').strip("'").strip(',')
        pyproject_deps[pkg.lower()] = ver

# Read requirements.txt
requirements_deps = {}
with open('requirements.txt', 'r') as f:
    for line in f:
        line = line.strip()
        if '==' in line and not line.startswith('#'):
            # Match package==version
            match = re.match(r'^([a-zA-Z0-9_-]+)==([0-9.]+)', line)
            if match:
                pkg, ver = match.groups()
                requirements_deps[pkg.lower()] = ver

# Find mismatches
mismatches = []
for pkg, pyproject_ver in pyproject_deps.items():
    req_ver = requirements_deps.get(pkg)
    if req_ver and req_ver != pyproject_ver:
        mismatches.append({
            'package': pkg,
            'pyproject': pyproject_ver,
            'requirements': req_ver
        })

if mismatches:
    print("MISMATCHES FOUND:")
    print("")
    for m in mismatches:
        print(f"  {m['package']}:")
        print(f"    pyproject.toml:   {m['pyproject']}")
        print(f"    requirements.txt: {m['requirements']}")
        print("")
else:
    print("✓ No version mismatches found")
PYEOF
```

### Step 2: Explain the Issue

If mismatches are found, explain:

```
WHY THIS CAUSES BUILD FAILURES:

In a hermetic build:
1. cachi2 prefetches dependencies from requirements.txt (version X)
2. pip install reads pyproject.toml (version Y)
3. pip looks for version Y in the hermetic cache
4. Version Y doesn't exist → Build fails

Example error:
  ERROR: Could not find a version that satisfies the requirement werkzeug==3.1.6
  ERROR: No matching distribution found for werkzeug==3.1.6
```

### Step 3: Determine Fix Strategy

Ask the user which version to use:

1. **Update pyproject.toml → requirements.txt version** (recommended for Renovate updates)
2. **Update requirements.txt → pyproject.toml version** (for manual updates)
3. **Specify a different version for both**

For automated updates (Renovate/Dependabot), default to option 1.

### Step 4: Apply the Fix

```bash
# Example: Update pyproject.toml to match requirements.txt
# (Adjust package name and versions based on detected mismatches)

echo "=== Applying fix ==="

# Update pyproject.toml
sed -i 's/werkzeug==3.1.6/werkzeug==3.1.9/' pyproject.toml

# Regenerate requirements.txt
uv pip compile pyproject.toml --generate-hashes --python-version 3.14 -o requirements.txt

# Attempt to regenerate requirements-build.txt (may fail with Python 3.14 bug)
pybuild-deps compile -o requirements-build.txt requirements.txt || \
    echo "⚠️  Could not regenerate requirements-build.txt (known issue with pybuild-deps + Python 3.14)"
```

### Step 5: Verify the Fix

```bash
echo "=== Verification ==="
echo ""

# Re-run mismatch detection
python3 <<'PYEOF'
import tomllib
import re

with open('pyproject.toml', 'rb') as f:
    pyproject = tomllib.load(f)
    
pyproject_deps = {}
for dep in pyproject.get('project', {}).get('dependencies', []):
    if '==' in dep:
        parts = dep.split('==')
        pkg = parts[0].strip().strip('"').strip("'")
        ver = parts[1].strip().strip('"').strip("'").strip(',')
        pyproject_deps[pkg.lower()] = ver

requirements_deps = {}
with open('requirements.txt', 'r') as f:
    for line in f:
        line = line.strip()
        if '==' in line and not line.startswith('#'):
            match = re.match(r'^([a-zA-Z0-9_-]+)==([0-9.]+)', line)
            if match:
                pkg, ver = match.groups()
                requirements_deps[pkg.lower()] = ver

mismatches = []
for pkg, pyproject_ver in pyproject_deps.items():
    req_ver = requirements_deps.get(pkg)
    if req_ver and req_ver != pyproject_ver:
        mismatches.append(f"{pkg}: {pyproject_ver} vs {req_ver}")

if mismatches:
    print("⚠️  Still have mismatches:")
    for m in mismatches:
        print(f"  - {m}")
    exit(1)
else:
    print("✓ All versions synchronized!")
    print("")
    print("Changed files:")
    print("  - pyproject.toml")
    print("  - requirements.txt")
    if Path('requirements-build.txt').exists():
        print("  - requirements-build.txt (if regeneration succeeded)")
PYEOF
```

### Step 6: Show Changes

```bash
echo ""
echo "=== Changes Made ==="
echo ""
git diff --stat pyproject.toml requirements.txt requirements-build.txt 2>/dev/null
```

## Notes

- **Source of truth**: `pyproject.toml` is the source of truth for direct dependencies
- **Lock file**: `requirements.txt` is the resolved lock file (includes transitive deps)
- **Hermetic builds**: require all dependencies to be pre-fetched from lock files
- **Renovate**: Often updates lock files without updating source files
- **pybuild-deps**: May fail with Python 3.14 due to a known bug - this is OK if werkzeug is a runtime dependency (not build)

## Common Scenarios

### Scenario 1: Renovate Updated Lock File Only

**Symptom**: Build fails after Renovate PR merged
**Fix**: Update `pyproject.toml` to match `requirements.txt`

### Scenario 2: Manual Update to pyproject.toml

**Symptom**: Changed version in `pyproject.toml`, build fails
**Fix**: Regenerate `requirements.txt` from `pyproject.toml`

### Scenario 3: Multiple Mismatches

**Symptom**: Several packages out of sync
**Fix**: Regenerate everything from `pyproject.toml`

## Commands Reference

```bash
# Regenerate requirements.txt from pyproject.toml
uv pip compile pyproject.toml --generate-hashes --python-version 3.14 -o requirements.txt

# Regenerate requirements-build.txt from requirements.txt
pybuild-deps compile -o requirements-build.txt requirements.txt

# Check for mismatches (quick)
diff <(grep "^[a-z]" pyproject.toml | grep "==" | sort) \
     <(grep "^[a-z].*==" requirements.txt | sed 's/ \\$//' | sort)
```

## After Running This Skill

1. Review the changes: `git diff`
2. Commit the synchronized files
3. Push and let CI verify the hermetic build succeeds

## Related Skills

- `regenerate-rpm-lockfile` - For RPM dependency issues
