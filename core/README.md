# Core

`core/` contains the application-wide foundation.

Put code here when it defines global rules, contracts, or policies that the rest of the app depends on, regardless of the concrete implementation.

Examples:
- application configuration
- global constants
- shared error types
- application-level exception handling
- cross-cutting rules used across features

Do **not** put external system integrations or IO implementations here.

If a module mainly talks to the database, browser, filesystem, network, or third-party services, it does **not** belong in `core/`.