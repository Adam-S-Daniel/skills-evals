"use strict";

const BASE_URL = "https://api.example.com";

async function getJson(path) {
  const response = await fetch(`${BASE_URL}${path}`);
  if (response.status !== 200) {
    throw new Error(`GET ${path} failed: ${response.status}`);
  }
  return response.json();
}

module.exports = { getJson };
