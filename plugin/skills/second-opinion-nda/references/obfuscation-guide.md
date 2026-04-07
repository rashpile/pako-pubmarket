# Obfuscation Guide for NDA-Safe Context

## Core Principles

1. **Never expose**: company names, product names, brand names, internal URLs, internal API endpoints, employee names, database names, internal service names, internal project codenames
2. **Always replace** with generic placeholders: `CompanyX`, `ProductA`, `ServiceAlpha`, `InternalAPI`, `UserService`, `DataStore`
3. **Never include real code** — describe logic in plain text wherever possible; use pseudocode only when structure or flow must be shown
4. **Safe to expose**: open-source library names, public API patterns, standard protocols, language features, framework conventions

## Replacement Table

| Category | Real Example | Sanitized |
|----------|-------------|-----------|
| Company | Acme Corp | `CompanyX` |
| Product | AcmeCloud Dashboard | `ProductA Dashboard` |
| Service | acme-auth-service | `AuthService` |
| URL | api.acme.internal/v2 | `internal-api/v2` |
| Database | acme_prod_db | `MainDatabase` |
| Employee | john.doe@acme.com | `developer@company` |
| Project | Project Phoenix | `ProjectAlpha` |
| Repo | acme/cloud-platform | `company/platform` |
| Config key | ACME_SECRET_KEY | `COMPANY_SECRET` |
| Domain | acme.com | `company.example` |

## Code Sanitization Rules

### Convert real code to pseudocode:

**Before (real code):**
```python
class AcmeAuthMiddleware:
    def __init__(self, acme_sso_client):
        self.sso = acme_sso_client
    
    async def verify(self, token):
        user = await self.sso.validate_acme_token(token)
        return AcmeUser(id=user.acme_id, role=user.acme_role)
```

**After (sanitized pseudocode):**
```
AuthMiddleware:
  - accepts SSO client dependency
  - verify(token):
    - validates token via SSO provider
    - returns User object with id and role
```

### What to preserve in pseudocode:
- Algorithm logic and flow
- Data structures (generic)
- Integration patterns
- Error handling approach
- Concurrency patterns

### What to strip:
- Class/function/variable names that reveal business domain
- String literals with company data
- Configuration values
- File paths revealing internal structure
- Comments referencing internal processes

## Open Source References — Safe to Include

These are always safe to mention by name:
- Language: Python, Go, TypeScript, Rust, Java, etc.
- Frameworks: React, FastAPI, Django, Spring Boot, Express, Next.js
- Libraries: pandas, numpy, requests, axios, lodash
- Databases: PostgreSQL, Redis, MongoDB, Elasticsearch
- Infrastructure: Docker, Kubernetes, Terraform, AWS/GCP/Azure services
- Protocols: REST, gRPC, GraphQL, WebSocket, OAuth2, OIDC

## Context Document Structure

Generate the sanitized context as:

```markdown
# External Consultation: [Topic]

## Goal
[What advice/feedback is needed — in generic terms]

## Background
[Sanitized project context — no company specifics]

## Current Approach (Pseudocode)
[Sanitized pseudocode of relevant logic]

## Technologies Used
[Open-source libs/frameworks — safe to list by name]

## Specific Questions
1. [Question 1]
2. [Question 2]
```