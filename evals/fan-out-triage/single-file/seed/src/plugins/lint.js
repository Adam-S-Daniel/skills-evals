module.exports = (acme) => {
  acme.hooks.preBuild((config) => {
    if (config.build.target === "node18") console.log("lint on node18");
  });
};
