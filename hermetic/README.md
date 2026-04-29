# Hermetic Build Support

This directory contains files used by Konflux/cachi2 to enable hermetic builds
(no network access during container build). All dependencies—Python packages and
RPMs—are prefetched before the build starts.

## Directory Contents

| File | Purpose |
|------|---------|
| `rpms.in.yaml` | Declares which RPM packages to prefetch and which repos to use |
| `rpms.lock.yaml` | Lockfile with resolved RPM URLs and checksums (generated) |
| `hummingbird.repo` | Yum repo definitions for Hummingbird (referenced by `rpms.in.yaml`) |
| `librdkafka/` | Git submodule of [librdkafka](https://github.com/confluentinc/librdkafka) source, built from source in the Dockerfile |

## How It Works

The Tekton pipelines in `.tekton/` specify hermetic build parameters:

```yaml
hermetic: "true"
prefetch-input: '[{"type": "pip", "path": "."}, {"type": "rpm", "path": "hermetic"}]'
```

Before the container build, cachi2 prefetches:
1. **Python packages** from `pyproject.toml` at the repo root
2. **RPM packages** from `hermetic/rpms.lock.yaml`

During the build, network access is blocked. cachi2 injects a
`/cachi2/cachi2.env` file that redirects pip and dnf5 to use the prefetched
dependencies.

## Regenerating the RPM Lockfile

When you add/remove RPM packages in `rpms.in.yaml` or update `hummingbird.repo`, you
need to regenerate `rpms.lock.yaml`.

### 1. Build the lockfile generator container (one-time setup)

```bash
git clone https://github.com/konflux-ci/rpm-lockfile-prototype.git
cd rpm-lockfile-prototype
podman build -t localhost/rpm-lockfile-prototype .
```

### 2. Generate the lockfile

From the repo root:

```bash
podman run --rm \
  -v "$HOME/.config/containers/auth.json:/root/.docker/config.json:ro" \
  -v "$(pwd):/workdir:z" \
  -w /workdir \
  localhost/rpm-lockfile-prototype \
  --outfile hermetic/rpms.lock.yaml \
  hermetic/rpms.in.yaml
```

The auth.json mount is needed so skopeo can pull the base image metadata from
the container registry.

## Updating librdkafka

librdkafka is vendored as a git submodule to avoid depending on external RPM
repos that aren't EC-approved. To update:

```bash
cd hermetic/librdkafka
git fetch --tags
git checkout v<new-version>
cd ../..
git add hermetic/librdkafka
git commit -m "Update librdkafka to v<new-version>"
```

Ensure the librdkafka version is compatible with the `confluent-kafka` Python
package version in `pyproject.toml` (librdkafka must be >= confluent-kafka
version).
