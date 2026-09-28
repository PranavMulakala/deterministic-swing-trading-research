# Stock-paper alert service preparation — September 24, 2026

The two one-shot units were **installed on the existing Droplet on September 24**, but no recurring timer is installed or enabled. The alert unit has not been started with its `--send` action. It runs the separate
GET-only Alpaca paper alert worker and can send only email. It has no broker
order method, automatic sale, position card, or timer. Existing IBKR, collector,
and frozen research services are not modified by the unit file.

The unit uses systemd `LoadCredential` to provide exactly three private files to
its short-lived process: a stock-only configuration, the existing Alpaca paper
credential, and the existing Resend email credential. It does not add the process
to the collector or IBKR groups and does not persist a second credential file.
The credential values are not displayed in logs. The owner approved this additional
process use of the two existing keys on September 24. The service's filesystem sandbox hides the original credential
directories from its process.

The private `/etc/stock-paper-alerts/config.json` now contains an ID locked from a
GET-only Alpaca paper account check, the existing report inbox, and
`email_enabled: true`. A position card remains absent until a specific paper
holding and target have been reviewed. No timer is in this package.

September 24 verification: 55 focused offline tests passed. Both units passed
server-side `systemd-analyze verify`. A labeled test email was accepted by the
provider and observed in the configured inbox at 10:26 a.m. Eastern; a rerun of
the same test ID reported `already_accepted` and made no second submission.
The GET-only paper read found an active account, zero positions and zero open
orders. A separate IEX LITE quote was current when checked, and a first news
page was accessible. An unprivileged worker run with no send flag returned
`no_paper_position`. These checks establish connectivity at that moment, not
continuous alert delivery or trading performance.
