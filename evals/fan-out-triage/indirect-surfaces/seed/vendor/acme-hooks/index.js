module.exports = function svgHooks(api) {
  api.registerTransform("svg", (source) => source.trim());
  api.onAsset((asset) => {
    if (asset.name.endsWith(".svg")) api.log(`optimized ${asset.name}`);
  });
};
