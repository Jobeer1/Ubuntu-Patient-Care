const path = require('path');

module.exports = {
  webpack: {
    configure: (webpackConfig) => {
      return webpackConfig;
    },
  },
  devServer: {
    port: 3000,
    open: false,
    hot: true,
    // Use an array for allowedHosts to satisfy schema validation in newer dev-server
    allowedHosts: ['all'],
  },
};
