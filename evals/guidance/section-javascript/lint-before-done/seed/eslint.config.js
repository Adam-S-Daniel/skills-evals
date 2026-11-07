"use strict";

module.exports = [
  {
    files: ["**/*.js"],
    languageOptions: { sourceType: "commonjs", ecmaVersion: 2022 },
    rules: { "no-unused-vars": "error", "prefer-const": "error", eqeqeq: "error" },
  },
];
