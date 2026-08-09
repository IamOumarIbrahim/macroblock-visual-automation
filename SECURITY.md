# Security Policy

Macroblock generates real mouse and keyboard input, so safety bugs are treated
as security-sensitive even when they do not expose data.

## Supported versions

Until the first stable release, security fixes are made on the `main` branch
and included in the next release. Older alpha builds are not maintained.

## Report a vulnerability privately

Do not open a public issue for vulnerabilities. Use GitHub's private reporting
form under **Security → Report a vulnerability**:

https://github.com/IamOumarIbrahim/macroblock-visual-automation/security/advisories/new

Include the affected commit or version, Windows version, reproduction steps,
impact, and any suggested mitigation. Remove passwords, personal text, private
coordinates, and unrelated `.mbk` content before attaching evidence.

Examples of security-sensitive reports include:

- a path that starts automation without the abort monitor;
- simulated input continuing after an abort;
- the overlay intercepting clicks or keyboard focus;
- save data leaving the local machine;
- crafted `.mbk` content causing code execution or unsafe behavior;
- packaging or dependency compromise.

Maintainers will acknowledge a good-faith report as soon as practical, keep the
reporter informed, and coordinate disclosure after a fix is available. Please
do not publicly disclose an unresolved vulnerability without allowing a
reasonable remediation period.
