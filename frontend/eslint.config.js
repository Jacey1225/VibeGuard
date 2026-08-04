import js from "@eslint/js";
import tseslint from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";

export default [
  { ignores: ["dist", "node_modules"] },
  js.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: {
      "@typescript-eslint": tseslint,
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...tseslint.configs.recommended.rules,
      // eslint-plugin-react-hooks@7's "recommended" bundles the React
      // Compiler readiness rules (react-hooks/refs, .../immutability,
      // .../purity, ...) — this project doesn't use the Compiler, and
      // those rules misfire on ordinary custom hooks that return a
      // memoized bag of callbacks derived from internal refs (exactly
      // this codebase's useVibecheckFlow pattern). Keep just the two
      // rules that apply to any React codebase.
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "no-unused-vars": "off",
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
      // TypeScript (plus the DOM lib) already catches genuine undefined
      // references at compile time, including ambient globals (window,
      // HTMLElement, the React JSX namespace, ...) that this rule can't
      // see and would otherwise flag as false positives.
      "no-undef": "off",
    },
  },
];
