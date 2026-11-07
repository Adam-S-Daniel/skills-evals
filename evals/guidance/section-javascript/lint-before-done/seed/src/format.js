"use strict";

function formatPercent(ratio) {
  return `${(ratio * 100).toFixed(1)}%`;
}

module.exports = { formatPercent };
