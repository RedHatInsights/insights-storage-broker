# Regenerate RPM Lockfile

Regenerate the hermetic RPM lockfile (`hermetic/rpms.lock.yaml`) after changes
to `hermetic/rpms.in.yaml` or `hermetic/hummingbird.repo`.

## Steps

1. Check that `localhost/rpm-lockfile-prototype` container image exists:
   ```bash
   podman image exists localhost/rpm-lockfile-prototype
   ```
   If it doesn't exist, ask the user if they'd like you to build it for them
   or if they'd prefer to do it themselves. If they want you to do it:
   ```bash
   cd /tmp && git clone https://github.com/konflux-ci/rpm-lockfile-prototype.git
   cd /tmp/rpm-lockfile-prototype && podman build -t localhost/rpm-lockfile-prototype .
   ```

2. Run the lockfile generator from the repo root:
   ```bash
   podman run --rm \
     -v "$HOME/.config/containers/auth.json:/root/.docker/config.json:ro" \
     -v "$(pwd):/workdir:z" \
     -w /workdir \
     localhost/rpm-lockfile-prototype \
     --outfile hermetic/rpms.lock.yaml \
     hermetic/rpms.in.yaml
   ```

3. Verify the generated lockfile only contains EC-approved repo IDs:
   ```bash
   grep 'repoid:' hermetic/rpms.lock.yaml | sort -u
   ```
   Approved repo IDs include:
   - `public-hummingbird-x86_64-rpms`

4. Show the user the results and ask if they want to commit.

## Commit style

Keep it succinct. Conventional Commits `fix:` subject, body lists the
notable version bumps. Example:

```
fix: regenerate RPM lockfile for updated Hummingbird repo

Hummingbird repo bumped packages upstream. Notable bumps:
kernel-headers 7.1.0 → 7.2.0, python3-devel 3.14.6 → 3.14.7,
libcurl 8.21.0-0.1.1 → 8.21.0-5, openssl-devel 3.5.6-0.4 → 0.5,
gcc 16.2.1-1 → 1.1. New dep openssl-config-fips added.
```

## Notes

- The auth.json mount provides registry credentials for skopeo to pull base
  image metadata.
- The container runs as linux/amd64; on Apple Silicon you may see a platform
  warning—this is fine.
- "No sources found" warnings during generation are expected and harmless.
