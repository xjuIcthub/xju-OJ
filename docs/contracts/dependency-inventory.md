# Dependency and Image Inventory Baseline

> Captured 2026-08-23. This is an inventory of the current main source and Compose declarations, not an approval to deploy them.

## Frontend dependency manager

- `frontend/package.json`: 52 production dependencies, 23 development dependencies.
- `frontend/yarn.lock`: Yarn lockfile v1 with 1,109 entry headers; no pnpm lock exists.
- `.nvmrc`: Node `14.21.3`; `package.json` engines are legacy lower bounds (`node >=4`, `npm >=3`).
- Key direct package families: Vue 2.5, Vue Router 3, Vuex 3, Vue I18n 7, Element UI 2, iView 2, Webpack 3, Babel 6, Axios 0.18, ECharts 3, CodeMirror-lite, Simditor tar packages, Sentry/Raven, Moment, and KaTeX.
- Ignored installed-tree probes found `jquery` and `codemirror` although they are not direct package declarations. This is an implicit-dependency finding for the pnpm lock Step.
- The local host has Node `v24.16.0`, npm `11.13.0`, and no `yarn` executable; the baseline build therefore ran through the package's existing `node_modules` with `npm run build` and did not regenerate a lockfile.

## Backend package pins

```text
coverage==6.5.0
django-cas-ng==5.0.1
django-dbconn-retry==0.1.7
django-dramatiq==0.11.6
django-redis==5.4.0
redis==4.6.0
Django==3.2.25
djangorestframework==3.14.0
dramatiq==1.16.0
entrypoints==0.4
Envelopes==0.4
flake8-coding==1.3.2
flake8-quotes==3.3.2
flake8==7.0.0
gunicorn==21.2.0
jsonfield==3.1.0
otpauth==1.0.1
pillow==10.2.0
psycopg2==2.9.9
python-dateutil==2.8.2
qrcode==7.4.2
raven==6.10.0
XlsxWriter==3.1.9
```

The current backend Dockerfile is `python:3.12-alpine`, while the Step 00 lock requires Python `>=3.10,<3.11` for future production backend/Judge images.

## Compose image declarations and immutable digests

| Current declaration | Registry metadata observed 2026-08-23 |
|---|---|
| `redis:4.0-alpine` | manifest `sha256:aaf7c123077a5e45ab2328b5ef7e201b5720616efac498d55e65a7afbb96ae20` |
| `postgres:10-alpine` | manifest `sha256:63cfb6eac6b362c7c994f22c3804c61b31898cf0cb52f8e7e86bd99a244f4366` |
| `registry.cn-hongkong.aliyuncs.com/oj-image/judge:1.6.1` | manifest `sha256:2dd902870f5e6f69866aa339a6a98b6da9eb1693e2e9936dce23d73203151501` |
| `registry.cn-hongkong.aliyuncs.com/oj-image/backend:1.6.1` | manifest `sha256:44282afa6fad7914f54c1c3d38b53e4b264b45533782ddeaef6525b4945bb836` |

The remote Compose image tags and local source-derived images are not assumed to be the same artifact. The digest evidence above makes that mismatch explicit for later replacement.

## Existing local image measurements

| Image | Size | Layers | Local image ID |
|---|---:|---:|---|
| `xju-oj-backend:stage03-final3` | 136,218,576 bytes | 9 | `sha256:99536577bd6004353225f833a6bb7144a341d91c51dee87644941da0a657cbd1` |
| `xju-oj-frontend:stage02-final` | 55,701,307 bytes | 10 | `sha256:b0dc8d04ea6ff7c4acf57cce15c6e8943e196da675fc84b14f38ec2fc057f578` |
| `postgres:10-alpine` | 79,090,044 bytes | 9 | `sha256:02c83b13f6ea0ddfe91471a401e2fb0db27667dd25fa3c501a5b465974f0865d` |
| `redis:4.0-alpine` | 20,435,464 bytes | 6 | `sha256:e3dd0e49bca555d559ca2e97f06a1efa108ebd230fddcb17606723994f18ae3b` |

No secret values, environment values, or credentials were included in this inventory.
