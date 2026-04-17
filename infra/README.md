# Infra

`infra/` contains concrete technical implementations and external integrations.

Put code here when it performs real IO or talks to systems outside the business/domain logic.

Examples:
- database engine/session setup
- browser automation
- filesystem and JSON read/write
- API clients
- format conversion tied to technical transport or storage
- logging implementation details

Do **not** put global business rules, shared domain contracts, or app-wide policies here.

If a module defines what the app means, it likely belongs in `core/`.
If it defines how the app technically interacts with the outside world, it belongs in `infra/`.