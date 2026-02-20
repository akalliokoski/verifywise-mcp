"""HTTP client for the VerifyWise REST API.

This module will implement the VerifyWiseClient in Phase 1.3.

VerifyWise API Routes (discovered from verifywise/Servers/routes/ at v2.1):
==========================================================================

Authentication:
  POST   /api/users/login                         - Login, returns access + refresh tokens
  POST   /api/users/refresh-token                 - Get new access token using refresh token
  POST   /api/users/check-user-exists             - Check if any user exists (setup flow)

Projects:
  GET    /api/projects                            - List all projects
  GET    /api/projects/:id                        - Get project by ID
  POST   /api/projects                            - Create project
  PUT    /api/projects/:id                        - Update project
  DELETE /api/projects/:id                        - Delete project
  GET    /api/projects/stats/:id                  - Get project stats
  GET    /api/projects/calculateProjectRisks/:id  - Risk calculations for project
  GET    /api/projects/calculateVendorRisks/:id   - Vendor risk calculations
  GET    /api/projects/compliance/progress/:id    - Compliance progress for project
  GET    /api/projects/assessment/progress/:id    - Assessment progress for project
  GET    /api/projects/all/compliance/progress    - Compliance progress across all projects
  GET    /api/projects/all/assessment/progress    - Assessment progress across all projects

Risks (Project Risks):
  GET    /api/projectRisks                        - List all risks
  GET    /api/projectRisks/by-projid/:id          - Risks by project ID
  GET    /api/projectRisks/by-frameworkid/:id     - Risks by framework ID
  GET    /api/projectRisks/:id                    - Get risk by ID
  POST   /api/projectRisks                        - Create risk
  PUT    /api/projectRisks/:id                    - Update risk
  DELETE /api/projectRisks/:id                    - Delete risk

Vendors:
  GET    /api/vendors                             - List all vendors
  GET    /api/vendors/:id                         - Get vendor by ID
  GET    /api/vendors/project-id/:id              - Vendors by project ID
  POST   /api/vendors                             - Create vendor
  PATCH  /api/vendors/:id                         - Update vendor
  DELETE /api/vendors/:id                         - Delete vendor

Vendor Risks:
  GET    /api/vendorRisks                         - List vendor risks
  GET    /api/vendorRisks/:id                     - Get vendor risk by ID
  POST   /api/vendorRisks                         - Create vendor risk
  PUT    /api/vendorRisks/:id                     - Update vendor risk
  DELETE /api/vendorRisks/:id                     - Delete vendor risk

Compliance:
  GET    /api/compliance/score                    - Compliance score for authenticated org
  GET    /api/compliance/score/:organizationId    - Compliance score for specific org (admin)
  GET    /api/compliance/details/:organizationId  - Detailed compliance breakdown (drill-down)

AI Model Inventory:
  GET    /api/modelInventory                      - List AI models
  GET    /api/modelInventory/:id                  - Get model by ID
  POST   /api/modelInventory                      - Create AI model record
  PUT    /api/modelInventory/:id                  - Update model
  DELETE /api/modelInventory/:id                  - Delete model

Frameworks:
  GET    /api/frameworks                          - List compliance frameworks
  GET    /api/eu-ai-act                           - EU AI Act framework data
  GET    /api/iso-42001                           - ISO 42001 framework data
  GET    /api/iso-27001                           - ISO 27001 framework data

Users:
  GET    /api/users                               - List all users
  GET    /api/users/:id                           - Get user by ID
  GET    /api/users/by-email/:email               - Get user by email
  POST   /api/users                               - Create user
  PUT    /api/users/:id                           - Update user
  DELETE /api/users/:id                           - Delete user

Port mappings:
  Backend API: http://localhost:3000  (env: VERIFYWISE_BASE_URL)
  Frontend:    http://localhost:8080
  EvalServer:  http://localhost:8000  (internal only)
"""

# TODO (Phase 1.3): Implement VerifyWiseClient
# See ARCHITECTURE.md "client.py — HTTP Client" section for design.
