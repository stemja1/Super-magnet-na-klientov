module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
  ],
  parser: "@typescript-eslint/parser",
  parserOptions: { ecmaVersion: 2020, sourceType: "module" },
  plugins: ["@typescript-eslint", "react-hooks"],
  ignorePatterns: ["dist", "node_modules", ".eslintrc.cjs", "src-tauri"],
  rules: {
    // The API client returns `any` in places where a response shape is not yet
    // modelled; keep the type-safety rules but not the no-explicit-any ban.
    "@typescript-eslint/no-explicit-any": "warn",
    "@typescript-eslint/no-unused-vars": [
      "error",
      { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
    ],
    "no-undef": "off",
  },
  overrides: [
    {
      files: ["*.cjs"],
      parser: "espree",
      parserOptions: { sourceType: "script" },
      rules: { "@typescript-eslint/no-require-imports": "off" },
    },
  ],
};
