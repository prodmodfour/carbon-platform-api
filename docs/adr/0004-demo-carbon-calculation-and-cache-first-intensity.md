# ADR 0004: Demo carbon calculation and cache-first intensity lookup

## Status

Accepted

## Context

The portfolio needs deterministic carbon-estimate behavior that is easy to test and safe to publish. It also needs to show how an external carbon intensity provider could be integrated without depending on a live third-party API during tests or local development.

Authoritative carbon accounting requires domain-specific datasets, assumptions, and validation that are outside this project scope.

## Decision

Use simple public-safe demo energy factors in `CarbonCalculationService`. Document those factors as sample values only, and make factor lookup and unit conversion replaceable through small protocols.

For carbon intensity lookup, separate the concerns:

```text
CarbonIntensityService
  -> cache read
  -> provider client call on cache miss
  -> cache write after successful provider response
```

Use a reserved `.invalid` provider base URL by default, isolate HTTP calls in `clients/`, isolate Redis access in `cache/`, and test provider behavior with fakes or `httpx.MockTransport`.

Usage ingestion currently accepts caller-supplied carbon intensity values. It does not call the provider/cache service yet.

## Consequences

- Unit tests are deterministic and do not depend on a live carbon provider.
- The calculation formula and extension points are visible and easy to review.
- The project avoids presenting demo factors as authoritative measurements.
- Redis serialization and external HTTP errors are testable behind interfaces.
- A future ingestion flow can use the carbon intensity service without changing route handlers or calculation internals.
