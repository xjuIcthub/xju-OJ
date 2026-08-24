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

export default defineConfig(({ mode }) => {
  const commit = process.env.GIT_COMMIT || 'unknown'
  const target = process.env.TARGET || 'http://127.0.0.1:8000'

  return {
    plugins: [vue(), copyStaticAssets()],
    base: '/',
    publicDir: false,
    resolve: {
      alias: {
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
      host: '0.0.0.0',
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
