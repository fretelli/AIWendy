# Release process

Maintainers release KeelTrader from a clean, protected `v2` branch.

1. Update `CHANGELOG.md` and choose a SemVer version.
2. Confirm the required CI, `Security gate`, and `Self-host gate` checks are green.
3. Open the Release workflow from the current `v2` branch and enter the SemVer tag plus the exact 40-character `v2` commit SHA.
4. Approve the protected `release` environment. The workflow rejects a non-current, unverified, unchecked, malformed, or conflicting release identity.
5. The workflow retests the exact commit, publishes API/Web images to GHCR, emits SBOM and provenance attestations, signs image digests with keyless Cosign, and creates the immutable version tag and GitHub Release.
6. Verify the release tag target, assets, image digests, attestations, and signatures before any production deployment consumes them.

Release tags are created only by the authorized workflow. Ordinary tag pushes do not trigger a release, and existing `v*` tags must not be updated or deleted.

Production deployment configuration is deliberately out of scope for this public repository. Operators should pin the published image digests in a private infrastructure repository and keep credentials, host paths, domains, monitoring, and rollback procedures there.
