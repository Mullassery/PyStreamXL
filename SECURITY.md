# Security Policy

## Reporting Security Issues

**DO NOT** open public GitHub issues for security vulnerabilities.

If you discover a security vulnerability, please email: **mullassery@gmail.com**

Include:
- Description of the vulnerability
- Steps to reproduce (if applicable)
- Potential impact
- Suggested fix (if you have one)

## Known Limitations & Mitigations

### This Version (0.4.0)

- **NO PRODUCTION USE** - This is a beta release
- Limited security hardening - see PRODUCTION_AUDIT_REPORT.md for details
- See PRODUCTION_AUDIT_REPORT.md for specific security issues

## Security Updates

Security patches will be released as minor/patch versions when vulnerabilities are discovered.

## Dependency Security

This project uses:
- Python 3.9+
- Rust 1.70+ (for Rust components)

Keep dependencies updated for latest security patches.

## Compliance & Certifications

This software is **NOT** currently:
- SOC 2 certified
- HIPAA compliant
- GDPR compliant
- PCI DSS compliant
- ISO 27001 certified

For compliance requirements, see PRODUCTION_AUDIT_REPORT.md.

## Development Security

When contributing:
- Do not commit secrets, credentials, or API keys
- Use environment variables for sensitive configuration
- Run security checks: `ruff check .`, `cargo clippy`
- Write tests for security-related code

## Questions?

For security questions (non-vulnerability): open a GitHub Discussion.
