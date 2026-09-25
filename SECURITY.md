# Security Policy

## Supported version

Security fixes are applied to the current `main` branch.

## Reporting a vulnerability

Please use **GitHub Private Vulnerability Reporting / Security Advisories** when possible.

Do not open a public issue containing working credentials, personal data, authentication tokens, private infrastructure details or a reproducible exploit against a live deployment.

## Baseline

- Secrets must be provided through environment variables or the hosting provider's secret store.
- Real credentials and production datasets must never be committed.
- Dependencies should be kept current through Dependabot where applicable.
- Demo/test data should be synthetic.
- If a credential is committed publicly, treat it as compromised and rotate it at the provider; deleting it from the latest commit is not sufficient.

Production requires a strong SECRET_KEY and server-side API credentials. CSRF, rate limiting and ownership checks must remain enabled.
