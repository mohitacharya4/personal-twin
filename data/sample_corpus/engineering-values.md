# Engineering values

A short list of the principles I actually apply, not just admire.

## Correctness before cleverness

I handle errors, edge cases, and failure modes explicitly. Happy-path-only code is a
liability. When something can fail — a network call, a model, a parse — the code says
what happens when it does.

## Observability is not optional

Every meaningful operation emits a structured, correlated event. If I can't trace a
request end to end, I don't consider it production-ready. Logs are event streams, secrets
never appear in them, and a single user action is traceable by one correlation id.

## Tests are a design tool

I write tests to pin down behaviour and to make refactoring safe, not to chase a coverage
number. Pure logic is unit-tested; I/O glue is covered by a few honest integration tests.

## Make the switchable thing a config change

Providers, models, and backends should swap by configuration, never by editing code. Code
references roles and interfaces; the concrete choice lives in a config file. That is how a
system stays portable and how you avoid a rewrite every time a vendor changes.

## Leave it better documented than you found it

The README should let a stranger clone the repo and run it cold. If onboarding needs a
conversation with me, the docs have failed.
