module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: ["eslint:recommended"],
  parser: "@typescript-eslint/parser",
  parserOptions: { ecmaVersion: 2020, sourceType: "module" },
  ignorePatterns: ["dist", "node_modules", ".eslintrc.cjs"],
  rules: {},
};
