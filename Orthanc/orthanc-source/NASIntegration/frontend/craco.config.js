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
    allowedHosts: 'all',
  },
};
