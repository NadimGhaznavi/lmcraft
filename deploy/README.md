# Bundled deployment inputs

`../MOO-1.9.0alpha/` is the original supplied LambdaMOO distribution. Its bytes
are unchanged. `moo-source.sha256` records every upstream file, including the
distribution's own `MANIFEST`. The installer builds in a separate directory
and never runs Autoconf or writes into the upstream source.

`LambdaCore-17May04.db` is the unmodified clean seed downloaded during initial
setup from https://lambda.moo.mud.org/pub/MOO/LambdaCore-17May04.db.

SHA-256: `e453a0d4f837db9969e2fa00250c3a58aafcf0d843d96495c1dd81924ebf4747`.

This is a seed, not the live world. No live database or credentials belong in
Git. Installation uses these local inputs and makes no source/world downloads.
