# Release process

Maintainers release KeelTrader from a clean, protected `v2` branch.

1. Update `CHANGELOG.md` and choose a SemVer version.
2. Confirm CI, CodeQL, dependency review, and the scheduled self-host clean-room workflow are green.
3. Create a signed annotated tag such as `v0.2.0` from the exact `v2` commit.
4. The release workflow tests the source, publishes API/Web images to GHCR, emits SBOM and provenance attestations, signs image digests with keyless Cosign, and creates a GitHub Release.
5. Verify the release assets and image attestations before any production deployment consumes the digests.

Production deployment configuration is deliberately out of scope for this public repository. Operators should pin the published image digests in a private infrastructure repository and keep credentials, host paths, domains, monitoring, and rollback procedures there.
