const normalize = names => Array.isArray(names) ? Object.fromEntries(names.map(name => [name, name])) : names

export const mapGetters = names => Object.fromEntries(Object.entries(normalize(names)).map(([local, remote]) => [local, function () { return this.$store.getters[remote] }]))
export const mapActions = names => Object.fromEntries(Object.entries(normalize(names)).map(([local, remote]) => [local, function (payload) { return this.$store.dispatch(remote, payload) }]))
export const mapMutations = names => Object.fromEntries(Object.entries(normalize(names)).map(([local, remote]) => [local, function (payload) { return this.$store.commit(remote, payload) }]))
export const mapState = names => Object.fromEntries(Object.entries(normalize(names)).map(([local, source]) => [local, function () {
  return typeof source === 'function' ? source.call(this, this.$store.state, this.$store.getters) : this.$store.state[source]
}]))
