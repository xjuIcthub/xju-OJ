import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const root = path.dirname(fileURLToPath(import.meta.url))
const resolve = (entry) => path.resolve(root, entry)

function copyStaticAssets () {
  return {
    name: 'copy-static-assets',
    closeBundle () {
      fs.cpSync(resolve('static'), resolve('dist/static'), { recursive: true })
    }
  }
}

const DEFAULT_AUTHENTIK_REGISTER_URL = 'https://auth.icthub.top/if/flow/icthub-public-registration/'

function envBoolean (name, fallback) {
  const value = process.env[name]
  if (value === undefined || value === '') return fallback
  return /^(1|true|yes|on)$/i.test(value)
}

function devRuntimeConfig () {
  const frontendDevMode = envBoolean('OJ_FRONTEND_DEV_MODE', false)
  return {
    APP_DOMAIN: process.env.APP_DOMAIN || '',
    PUBLIC_BASE_URL: process.env.PUBLIC_BASE_URL || '/public',
    VERSION: process.env.GIT_COMMIT || 'dev',
    OJ_FRONTEND_DEV_MODE: frontendDevMode,
    DEV_LOGIN_USERNAME: frontendDevMode ? (process.env.OJ_DEV_ADMIN_USERNAME || 'admin') : '',
    DEV_LOGIN_PASSWORD: frontendDevMode ? (process.env.OJ_DEV_ADMIN_PASSWORD || '12345678') : '',
    AUTHENTIK_OIDC_ENABLED: frontendDevMode ? false : envBoolean('AUTHENTIK_OIDC_ENABLED', false),
    AUTHENTIK_OIDC_REGISTER_URL: process.env.AUTHENTIK_OIDC_REGISTER_URL || DEFAULT_AUTHENTIK_REGISTER_URL,
    AUTHENTIK_LOCAL_LOGIN_ENABLED: frontendDevMode ? true : envBoolean('AUTHENTIK_LOCAL_LOGIN_ENABLED', true),
    AUTHENTIK_LOCAL_REGISTER_ENABLED: frontendDevMode ? true : envBoolean('AUTHENTIK_LOCAL_REGISTER_ENABLED', true)
  }
}

function devRuntimeConfigPlugin () {
  return {
    name: 'dev-runtime-config',
    configureServer (server) {
      server.middlewares.use((req, res, next) => {
        const pathname = (req.url || '').split('?', 1)[0]
        // Vite's default SPA fallback serves the first HTML entry for direct
        // history requests. Keep the admin entry isolated in dev so
        // `/admin/login` behaves like the production double-entry build.
        if (pathname.startsWith('/admin/') && pathname !== '/admin/index.html' && !path.extname(pathname)) {
          req.url = '/admin/index.html'
          return next()
        }
        if (pathname !== '/runtime-config.js' || !['GET', 'HEAD'].includes(req.method)) return next()

        const body = `window.__XJU_RUNTIME_CONFIG__ = ${JSON.stringify(devRuntimeConfig(), null, 2)}\n`
        res.statusCode = 200
        res.setHeader('Content-Type', 'application/javascript; charset=utf-8')
        res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate')
        res.end(req.method === 'HEAD' ? undefined : body)
      })
    }
  }
}

export default defineConfig(({ mode }) => {
  const commit = process.env.GIT_COMMIT || 'unknown'
  const target = process.env.TARGET || 'http://127.0.0.1:8000'
  const devHost = process.env.VITE_DEV_HOST || '127.0.0.1'
  const useDevelopmentFixtures = mode === 'development' && envBoolean('OJ_FRONTEND_DEV_MODE', false)

  return {
    plugins: [devRuntimeConfigPlugin(), vue(), copyStaticAssets()],
    base: '/',
    publicDir: false,
    resolve: {
      alias: {
        '@oj/mocks/fixtures': resolve(useDevelopmentFixtures ? 'src/pages/oj/mocks/fixtures.js' : 'src/pages/oj/mocks/empty-fixtures.js'),
        '@': resolve('src'),
        '@oj': resolve('src/pages/oj'),
        '@admin': resolve('src/pages/admin'),
        '~': resolve('src/components')
      },
      extensions: ['.mjs', '.js', '.jsx', '.json', '.vue']
    },
    define: {
      'process.env.NODE_ENV': JSON.stringify(mode),
      'process.env.VERSION': JSON.stringify(commit),
      'process.env.USE_SENTRY': JSON.stringify(process.env.USE_SENTRY || '0')
    },
    css: {
      preprocessorOptions: {
        less: {
          javascriptEnabled: true
        }
      }
    },
    server: {
      host: devHost,
      port: Number(process.env.PORT || 8080),
      proxy: {
        '/api': {
          target,
          changeOrigin: true,
          configure (proxy) {
            proxy.on('proxyReq', (proxyReq) => {
              proxyReq.setHeader('Referer', target)
            })
          }
        },
        '/public': {
          target,
          changeOrigin: true,
          configure (proxy) {
            proxy.on('proxyReq', (proxyReq) => {
              proxyReq.setHeader('Referer', target)
            })
          }
        }
      }
    },
    build: {
      outDir: resolve('dist'),
      emptyOutDir: true,
      sourcemap: process.env.USE_SENTRY === '1',
      rollupOptions: {
        input: {
          index: resolve('index.html'),
          admin: resolve('admin/index.html')
        },
        output: {
          entryFileNames: 'static/js/[name]-[hash].js',
          chunkFileNames: 'static/js/[name]-[hash].js',
          assetFileNames: 'static/assets/[name]-[hash][extname]'
        }
      }
    }
  }
})
