module.exports = function svgHooks(api) {
  api.registerTransform("svg", (source) => source.replace(/<!--[\s\S]*?-->/g, ""));
  api.onAsset((asset) => {
    if (asset.name.endsWith(".svg")) api.log(`optimized ${asset.name}`);
  });
};
