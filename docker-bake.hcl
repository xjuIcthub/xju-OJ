variable "GIT_SHA" {
  default = "local"
}

variable "IMAGE_REGISTRY" {
  default = "xju-oj"
}

variable "CACHE_REGISTRY" {
  default = ""
}

variable "BUILD_VERSION" {
  default = "phase1"
}

group "default" {
  targets = ["frontend", "backend", "judge-toolchain", "server"]
}

target "_common" {
  platforms = ["linux/amd64"]
  args = {
    GIT_COMMIT    = "${GIT_SHA}"
    VCS_REF      = "${GIT_SHA}"
    BUILD_VERSION = "${BUILD_VERSION}"
  }
  labels = {
    "org.opencontainers.image.source"   = "xju-OJ"
    "org.opencontainers.image.revision" = "${GIT_SHA}"
    "org.opencontainers.image.version"  = "${BUILD_VERSION}"
  }
}

target "frontend" {
  inherits   = ["_common"]
  context    = "./frontend"
  dockerfile = "Dockerfile"
  target     = "frontend-runtime"
  tags       = ["${IMAGE_REGISTRY}/frontend:git-${GIT_SHA}"]
  cache-from = CACHE_REGISTRY != "" ? ["type=registry,ref=${CACHE_REGISTRY}/frontend:buildcache"] : []
  cache-to   = CACHE_REGISTRY != "" ? ["type=registry,ref=${CACHE_REGISTRY}/frontend:buildcache,mode=max"] : []
}

target "backend" {
  inherits   = ["_common"]
  context    = "./backend"
  dockerfile = "Dockerfile"
  target     = "backend-runtime"
  tags       = ["${IMAGE_REGISTRY}/backend:git-${GIT_SHA}"]
  cache-from = CACHE_REGISTRY != "" ? ["type=registry,ref=${CACHE_REGISTRY}/backend:buildcache"] : []
  cache-to   = CACHE_REGISTRY != "" ? ["type=registry,ref=${CACHE_REGISTRY}/backend:buildcache,mode=max"] : []
}

target "judge-toolchain" {
  inherits   = ["_common"]
  context    = "./server"
  dockerfile = "Dockerfile"
  target     = "judge-toolchain"
  tags       = ["${IMAGE_REGISTRY}/judge-toolchain:tc-${GIT_SHA}"]
  cache-from = CACHE_REGISTRY != "" ? ["type=registry,ref=${CACHE_REGISTRY}/judge-toolchain:buildcache"] : []
  cache-to   = CACHE_REGISTRY != "" ? ["type=registry,ref=${CACHE_REGISTRY}/judge-toolchain:buildcache,mode=max"] : []
}

target "server" {
  inherits   = ["_common"]
  context    = "./server"
  dockerfile = "Dockerfile"
  target     = "judge-server"
  tags       = ["${IMAGE_REGISTRY}/server:git-${GIT_SHA}"]
  cache-from = CACHE_REGISTRY != "" ? ["type=registry,ref=${CACHE_REGISTRY}/server:buildcache"] : []
  cache-to   = CACHE_REGISTRY != "" ? ["type=registry,ref=${CACHE_REGISTRY}/server:buildcache,mode=max"] : []
}
