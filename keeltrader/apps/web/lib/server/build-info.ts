export type WebBuildInfo = {
  status: "ok";
  service: "keeltrader-web";
  git_sha: string;
  build_time: string;
  build_type: string;
};

export function getWebBuildInfo(
  env: Partial<NodeJS.ProcessEnv> = process.env
): WebBuildInfo {
  return {
    status: "ok",
    service: "keeltrader-web",
    git_sha: env.KEELTRADER_GIT_SHA || "unknown",
    build_time: env.KEELTRADER_BUILD_TIME || "unknown",
    build_type: env.KEELTRADER_BUILD_TYPE || "unknown",
  };
}
