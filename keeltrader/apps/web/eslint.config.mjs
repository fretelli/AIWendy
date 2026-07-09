import nextCoreWebVitals from "eslint-config-next/core-web-vitals";

const config = [
  ...nextCoreWebVitals,
  {
    ignores: [
      ".next/**",
      "coverage/**",
      "node_modules/**",
    ],
  },
];

export default config;
