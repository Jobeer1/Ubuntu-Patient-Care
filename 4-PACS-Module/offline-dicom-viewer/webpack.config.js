const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const CopyWebpackPlugin = require('copy-webpack-plugin');

module.exports = {
  entry: './src/app.js',
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'bundle.js',
    clean: true
  },
  module: {
    rules: [
      {
        test: /\.css$/i,
        use: ['style-loader', 'css-loader']
      },
      {
        test: /\.(png|svg|jpg|jpeg|gif|ico)$/i,
        type: 'asset/resource'
      },
      {
        test: /\.(woff|woff2|eot|ttf|otf)$/i,
        type: 'asset/resource'
      }
    ]
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: './index.html',
      title: 'SA Offline DICOM Viewer'
    }),
    new CopyWebpackPlugin({
      patterns: [
        { from: 'assets', to: 'assets' },
        { from: 'styles', to: 'styles' },
        { from: 'node_modules/cornerstone-core/dist/cornerstone.min.js', to: 'js/cornerstone.min.js' },
        { from: 'node_modules/cornerstone-tools/dist/cornerstoneTools.min.js', to: 'js/cornerstoneTools.min.js' },
        { from: 'node_modules/cornerstone-web-image-loader/dist/cornerstoneWebImageLoader.min.js', to: 'js/cornerstoneWebImageLoader.min.js' },
        { from: 'node_modules/cornerstone-wado-image-loader/dist/cornerstoneWADOImageLoader.bundle.min.js', to: 'js/cornerstoneWADOImageLoader.min.js' },
        { from: 'node_modules/dicom-parser/dist/dicomParser.min.js', to: 'js/dicomParser.min.js' },
        { from: 'node_modules/hammerjs/hammer.min.js', to: 'js/hammer.min.js' },
        { from: 'node_modules/localforage/dist/localforage.min.js', to: 'js/localforage.min.js' },
        { from: 'node_modules/dexie/dist/dexie.min.js', to: 'js/dexie.min.js' },
        { from: 'node_modules/jszip/dist/jszip.min.js', to: 'js/jszip.min.js' },
        { from: 'node_modules/file-saver/dist/FileSaver.min.js', to: 'js/FileSaver.min.js' },
        { from: 'node_modules/pdf-lib/dist/pdf-lib.min.js', to: 'js/pdf-lib.min.js' },
        { from: 'node_modules/html2canvas/dist/html2canvas.min.js', to: 'js/html2canvas.min.js' },
        { from: 'node_modules/crypto-js/crypto-js.js', to: 'js/crypto-js.min.js' }
      ]
    })
  ],
  devServer: {
    static: './dist',
    port: 8080,
    open: true,
    hot: true
  },
  resolve: {
    extensions: ['.js', '.json']
  }
};
