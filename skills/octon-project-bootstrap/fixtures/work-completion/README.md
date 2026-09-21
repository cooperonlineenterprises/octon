# Governed work-completion fixtures

`valid-config.json` is a domain-neutral enabled configuration used only by
tests. It is not project authority or a provider assertion.

`invalid-mutations.json` lists one-fault mutations that the generated runtime
validator or completion engine must reject or block. Tests apply each mutation
to a fresh valid subject so a happy-path fixture cannot conceal missing
negative enforcement.
