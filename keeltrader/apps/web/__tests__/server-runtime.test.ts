/**
 * @jest-environment node
 */

import { getWebBuildInfo } from "../lib/server/build-info";
import {
  getApiBaseUrlCandidates,
  getResearchBaseUrl,
} from "../lib/server/upstreams";

describe("server runtime helpers", () => {
  it("returns build metadata from the environment", () => {
    expect(
      getWebBuildInfo({
        KEELTRADER_GIT_SHA: "abc123",
        KEELTRADER_BUILD_TIME: "2026-01-02T03:04:05Z",
        KEELTRADER_BUILD_TYPE: "overlay",
      })
    ).toEqual({
      status: "ok",
      service: "keeltrader-web",
      git_sha: "abc123",
      build_time: "2026-01-02T03:04:05Z",
      build_type: "overlay",
    });
  });

  it("falls back to unknown build metadata", () => {
    expect(getWebBuildInfo({})).toEqual({
      status: "ok",
      service: "keeltrader-web",
      git_sha: "unknown",
      build_time: "unknown",
      build_type: "unknown",
    });
  });

  it("adds localhost fallback when api service URL is configured", () => {
    expect(
      getApiBaseUrlCandidates({ NEXT_PUBLIC_API_URL: "http://api:8000/api" })
    ).toEqual(["http://api:8000", "http://localhost:8000"]);
  });

  it("adds docker fallback when localhost URL is configured", () => {
    expect(
      getApiBaseUrlCandidates({ KEELTRADER_API_URL: "http://localhost:8000/" })
    ).toEqual(["http://localhost:8000", "http://api:8000"]);
  });

  it("uses default API upstream candidates when none are configured", () => {
    expect(getApiBaseUrlCandidates({})).toEqual([
      "http://localhost:8000",
      "http://api:8000",
    ]);
  });

  it("normalizes the research base URL", () => {
    expect(
      getResearchBaseUrl({
        RESEARCH_API_URL: "https://research.joyeeassets.com/api/",
      })
    ).toBe("https://research.joyeeassets.com");
  });
});
