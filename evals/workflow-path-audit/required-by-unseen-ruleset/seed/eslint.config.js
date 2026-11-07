module.exports = [
  {
    files: ["src/**/*.js", "test/**/*.js"],
    languageOptions: { ecmaVersion: 2022, sourceType: "commonjs" },
    rules: { "no-unused-vars": "error", eqeqeq: "error" },
  },
];
