const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  app.use(
    '/scheduler',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
      secure: false,
      logLevel: 'debug',
      onProxyReq: function(proxyReq, req, res) {
        console.log('Proxying request:', req.method, req.url, 'to', proxyReq.path);
      },
      onProxyRes: function(proxyRes, req, res) {
        console.log('Received response:', proxyRes.statusCode, req.url);
      },
      pathRewrite: {
        '^/scheduler': '/scheduler',  // keep the /scheduler prefix
      },
    })
  );
}; 