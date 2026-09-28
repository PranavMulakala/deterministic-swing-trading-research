# Deployment status: deliberately nondeployable

No service, timer, installer, remote path, runtime user, or rollback command is
provided in this version. The server identity and immutable installation path
were not verified, and the observer deliberately exits 2 with an overall
`BLOCKED` verdict. Shipping a guessed unit would turn a truthful local diagnostic
into a misleading failed service.

Run `observer.py` locally and read-only when reviewing the frozen package. Build
a separately versioned, allowlisted, hash-verified release only after the missing
data and lifecycle work is complete and the actual host path/user/service policy
has been verified. That later release must use a private network namespace,
deny IP traffic, accept exit 2 explicitly if it can still block, install without
credentials/archive access, and include an independently tested rollback. No
existing cloud service was changed or restarted for this package.
