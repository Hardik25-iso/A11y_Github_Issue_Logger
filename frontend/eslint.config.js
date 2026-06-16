import reactHooks from "eslint-plugin-react-hooks";

export default [
  {
    files: ["src/**/*.{js,jsx}"],
    plugins: { "react-hooks": reactHooks },
    languageOptions: {
      ecmaVersion: 2024,
      sourceType: "module",
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: {
        document: "readonly",
        fetch: "readonly",
        navigator: "readonly",
        window: "readonly",
      },
    },
    rules: {
      "no-undef": "error",
      ...reactHooks.configs.recommended.rules,
      // intentional one-shot effects: generate/search fire once on mount
      "react-hooks/exhaustive-deps": "warn",
    },
  },
];
