# DisputeSentry AI Behavior Catalog

This catalog enumerates the atomic, testable behaviors, domain rules, API contracts, security sanitizers, and performance metrics implemented in DisputeSentry AI.

---

## 1. Master Behavior Index

| ID | Title | Kind | Severity | Verification Status | Fixture Path |
|---|---|---|---|---|---|
| [DSP001](file:///D:/fix/challenges/paypal/catalog/DSP001.yaml) | Verify valid PayPal webhook signature | endpoint | error | docs-cited | `catalog/fixtures/DSP001/` |
| [DSP002](file:///D:/fix/challenges/paypal/catalog/DSP002.yaml) | Reject tampered or invalid webhook signature | endpoint | error | docs-cited | `catalog/fixtures/DSP002/` |
| [DSP003](file:///D:/fix/challenges/paypal/catalog/DSP003.yaml) | Deduplicate redelivered webhook events | behavior | info | docs-cited | `catalog/fixtures/DSP003/` |
| [DSP004](file:///D:/fix/challenges/paypal/catalog/DSP004.yaml) | Validate webhook certificate URL host domain | rule | error | docs-cited | `catalog/fixtures/DSP004/` |
| [DSP005](file:///D:/fix/challenges/paypal/catalog/DSP005.yaml) | Validate allowed dispute action links before API dispatch | contract | error | docs-cited | `catalog/fixtures/DSP005/` |
| [DSP006](file:///D:/fix/challenges/paypal/catalog/DSP006.yaml) | Match dispute to internal merchant fulfillment record | behavior | warning | docs-cited | `catalog/fixtures/DSP006/` |
| [DSP007](file:///D:/fix/challenges/paypal/catalog/DSP007.yaml) | Validate Seller Protection for Item Not Received claims | rule | error | docs-cited | `catalog/fixtures/DSP007/` |
| [DSP008](file:///D:/fix/challenges/paypal/catalog/DSP008.yaml) | Validate Seller Protection for Unauthorised claims | rule | error | docs-cited | `catalog/fixtures/DSP008/` |
| [DSP009](file:///D:/fix/challenges/paypal/catalog/DSP009.yaml) | Compile evidence for Significantly Not As Described claims | rule | warning | docs-cited | `catalog/fixtures/DSP009/` |
| [DSP010](file:///D:/fix/challenges/paypal/catalog/DSP010.yaml) | Calculate dispute response deadline and urgency tier | behavior | warning | docs-cited | `catalog/fixtures/DSP010/` |
| [DSP011](file:///D:/fix/challenges/paypal/catalog/DSP011.yaml) | Calculate Net Expected Recovery ROI for contest vs concede | rule | error | docs-cited | `catalog/fixtures/DSP011/` |
| [DSP012](file:///D:/fix/challenges/paypal/catalog/DSP012.yaml) | Dispatch inquiry communication in INQUIRY lifecycle stage | behavior | info | docs-cited | `catalog/fixtures/DSP012/` |
| [DSP013](file:///D:/fix/challenges/paypal/catalog/DSP013.yaml) | Enforce human approval gate for high-value decisions | rule | warning | docs-cited | `catalog/fixtures/DSP013/` |
| [DSP014](file:///D:/fix/challenges/paypal/catalog/DSP014.yaml) | Execute provide-evidence API call with tracking details | endpoint | error | docs-cited | `catalog/fixtures/DSP014/` |
| [DSP015](file:///D:/fix/challenges/paypal/catalog/DSP015.yaml) | Execute accept-claim API call when conceding dispute | endpoint | error | docs-cited | `catalog/fixtures/DSP015/` |
| [DSP016](file:///D:/fix/challenges/paypal/catalog/DSP016.yaml) | Enforce evidence attachment file size limits | rule | error | docs-cited | `catalog/fixtures/DSP016/` |
| [DSP017](file:///D:/fix/challenges/paypal/catalog/DSP017.yaml) | Validate evidence attachment file formats and MIME types | rule | error | docs-cited | `catalog/fixtures/DSP017/` |
| [DSP018](file:///D:/fix/challenges/paypal/catalog/DSP018.yaml) | Safeguard pending approvals approaching response deadline | behavior | error | docs-cited | `catalog/fixtures/DSP018/` |
| [DSP019](file:///D:/fix/challenges/paypal/catalog/DSP019.yaml) | Redact Primary Account Numbers and card data (PCI DSS) | rule | error | docs-cited | `catalog/fixtures/DSP019/` |
| [DSP020](file:///D:/fix/challenges/paypal/catalog/DSP020.yaml) | Neutralize prompt injection attempts in customer claims | rule | error | docs-cited | `catalog/fixtures/DSP020/` |
| [DSP021](file:///D:/fix/challenges/paypal/catalog/DSP021.yaml) | Compute win rate and net recovery metrics | metric | info | docs-cited | `catalog/fixtures/DSP021/` |
| [DSP022](file:///D:/fix/challenges/paypal/catalog/DSP022.yaml) | Append immutable state transition audit log with SHA-256 hash | behavior | error | docs-cited | `catalog/fixtures/DSP022/` |

---

## 2. Domain Matrix: Dispute Reason vs. Evidence & Seller Protection

| Dispute Reason | Applicable Evidence Type | Compulsory Evidence Fields | Seller Protection Requirement | Default Win Expectation |
|---|---|---|---|---|
| `MERCHANDISE_OR_SERVICE_NOT_RECEIVED` | `PROOF_OF_FULFILLMENT` | Carrier name, tracking number, delivery confirmation status (`DELIVERED`) | Online tracking must show delivery to transaction recipient address prior to dispute open time [10]. | High ($\ge 0.85$) if tracking confirms delivery; Low ($\le 0.15$) if tracking lost or missing. |
| `UNAUTHORISED` | `PROOF_OF_FULFILLMENT` | Carrier name, tracking number, shipment dispatch timestamp | Proof of shipment must be dated prior to PayPal dispute notification time [10]. | High ($\ge 0.80$) if shipped prior to dispute notification; Low ($\le 0.10$) if shipped post-notification. |
| `MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED` | `OTHER` or `PROOF_OF_REFUND` | Return policy URL/text, refund transaction ID, buyer comms | Item significantly not as described claims are not covered by Seller Protection; requires proving item met description or buyer agreement [9][10]. | Moderate ($\approx 0.40 - 0.50$); heavily depends on proof of refund or return refusal. |

---

## 3. Domain Matrix: Lifecycle Stage vs. Allowed API Operations

| Dispute Lifecycle Stage | Status | Allowed Actions & Rel Links | Execution Endpoint |
|---|---|---|---|
| `INQUIRY` | `WAITING_FOR_SELLER_RESPONSE` | `send_message`, `make_offer`, `accept_claim`, `escalate` | `POST /v1/customer/disputes/{id}/send-message`<br>`POST /v1/customer/disputes/{id}/accept-claim` |
| `CHARGEBACK` | `WAITING_FOR_SELLER_RESPONSE` | `provide_evidence`, `accept_claim` | `POST /v1/customer/disputes/{id}/provide-evidence`<br>`POST /v1/customer/disputes/{id}/accept-claim` |
| `PRE_ARBITRATION` | `UNDER_REVIEW` | None (read-only monitoring in v1) | `GET /v1/customer/disputes/{id}` |
| `RESOLVED` | `RESOLVED` | None (concluded) | Ingest `CUSTOMER.DISPUTE.RESOLVED` webhook |

---

## 4. Domain Matrix: Decision Routing & Approval Gate

| Condition / Financial Exposure | Calculated $P_{\text{win}}$ | Calculated Expected Value (EV) | Decision State | Action Trigger |
|---|---|---|---|---|
| Amount $< \$100.00$ AND Confidence $> 0.65$ | $\ge 0.70$ | $> 0$ | `AUTO_EXECUTING` | Submit evidence (`provide-evidence`) |
| Amount $< \$100.00$ AND Confidence $> 0.65$ | $< 0.30$ | $\le 0$ | `AUTO_EXECUTING` | Accept claim (`accept-claim`) |
| Amount $\ge \$100.00$ (High Exposure) | Any | Any | `PENDING_APPROVAL` | Operator must review and call `/approve` |
| Any Amount AND Confidence $\le 0.65$ | $0.30 - 0.69$ | Any | `PENDING_APPROVAL` | Operator review required due to uncertainty |
| Pending Approval remaining time $< 24$ hrs | Any | Any | `URGENT_APPROVAL` | High-priority alert triggered |
| Pending Approval remaining time $< 2$ hrs | $\ge 0.50$ | Any | `SAFETY_FALLBACK` | Auto-submit existing tracking proof to avoid default forfeiture |
