# Release process

Maintainers release KeelTrader from a clean, protected `v2` branch.

1. Update `CHANGELOG.md` and choose a SemVer version.
2. Confirm the required CI, `Security gate`, and `Self-host gate` checks are green.
3. Verify the release commit and create an SSH-signed annotated tag such as `v0.3.0` from the exact `v2` commit. Existing tags are immutable.
4. The release workflow verifies the tag against `.github/allowed_signers` before it tests or builds.
5. The workflow publishes API/Web images to GHCR, emits SBOM and provenance attestations, signs image digests with keyless Cosign, and creates a GitHub Release.
6. Verify the release assets, image digests, attestations, and signatures before any production deployment consumes them.

Production deployment configuration is deliberately out of scope for this public repository. Operators should pin the published image digests in a private infrastructure repository and keep credentials, host paths, domains, monitoring, and rollback procedures there.
