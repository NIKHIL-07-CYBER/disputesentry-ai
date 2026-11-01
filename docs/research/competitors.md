# Competitor and Adjacent Solutions Research

This document analyzes existing tools, libraries, commercial platforms, and open-source packages addressing dispute and chargeback management for PayPal and adjacent payment processors.

## Competitor Matrix

| Product | What it does | Language / Platform | License | Last Release | Strengths | Gaps |
|---|---|---|---|---|---|---|
| **Chargeflow** | Automated chargeback dispute and evidence representment platform connecting to PayPal, Stripe, Shopify. | Closed SaaS / Cloud API | Proprietary commercial | Continuous (v2 API active Oct 2026) | Turnkey evidence generation; wide processor integration; automatic submission. | Closed source; expensive success-fee pricing (~25% of recovered amount); opaque rule engine with no local merchant audit trail or deterministic rule inspection. |
| **Justt** | Enterprise-grade chargeback automation using custom dispute ROI models and tailored representment packages. | Closed SaaS | Proprietary commercial | Continuous (Oct 2026 enterprise release) | Sophisticated ROI evaluation on whether contesting is profitable; customized evidence narratives for enterprise volumes. | High enterprise entry threshold; not accessible to small/mid-market SMBs; no PayPal developer sandbox integration for testing or transparent code evaluation. |
| **Disputifier** | Chargeback representment automation for Shopify, PayPal, and Stripe with automated win-tracking. | Closed SaaS | Proprietary commercial | Continuous (Sep 2026) | Simple setup for Shopify merchants; covers PayPal disputes; performance-based fee structure. | Closed-source vendor lock-in; lacks open webhook verification primitives; no fine-grained human approval thresholds or customizable Seller Protection rule engines. |
| **Stripe Smart Disputes** | Native AI/rules-based chargeback evidence compiler embedded directly in Stripe Dashboard. | Cloud Platform Feature (Go/Java backend) | Proprietary platform service | Oct 2026 (Stripe Docs update) | Deep native integration with payment records; automatic file formatting and submission; zero setup for Stripe users. | Restricted exclusively to Stripe transactions; cannot ingest or resolve PayPal Disputes API v1 claims; lacks merchant-specific internal communication lookup. |
| **AgentGuard CB** (`agentguard-cb`) | Open-source CLI and library compiling deterministic evidence payloads for credit card chargebacks. | Python | MIT License | Aug 2026 (v0.3.1) | Open source; deterministic rule execution; human approval staging before API submission; no LLM hallucinations. | Exclusively focused on Stripe chargeback schemas; completely lacks PayPal Disputes API v1 integration, PayPal webhook verification, and PayPal Seller Protection logic. |
| **disputeguard** | Open-source validation library for Visa & Mastercard dispute reason codes and evidence requirements. | Python | Apache-2.0 | Jun 2026 (v0.1.0) | Strict validation of scheme rules, card network reason codes, and compulsory compelling evidence documents. | Narrow focus on card network rules; no active API execution engine, no webhook listener, and no support for PayPal internal inquiry/dispute workflows. |

## Differentiation

Based on the critical gaps identified across commercial SaaS and open-source tooling, **DisputeSentry AI** differentiates itself through three core advantages:

1. **First Open-Source PayPal Disputes Engine with Deterministic Seller Protection Alignment**
   Unlike closed SaaS tools (Chargeflow, Justt) or Stripe-only utilities (AgentGuard CB), DisputeSentry AI is purpose-built for the PayPal Disputes API v1. It bridges PayPal's strict Seller Protection eligibility criteria (verifiable tracking numbers, address matching, delivery dates) with automated evidence compilation and official API execution (`provide-evidence`, `accept-claim`).

2. **Economic Net Expected Recovery Modeling (Contest vs. Concede ROI)**
   Existing open tools blindly contest or rely on generic templates, ignoring dispute fee economics ($15 standard fee, $20 chargeback fee). DisputeSentry AI computes an explicit Net Expected Recovery formula:
   $$\text{EV} = (P_{\text{win}} \times \text{Dispute Amount}) - ((1 - P_{\text{win}}) \times \text{Dispute Fee}) - \text{Overhead}$$
   It automatically recommends conceding when expected value is net negative, saving merchants from wasting fees on unwinnable low-dollar claims.

3. **Verifiable State-Locked Human-in-the-Loop Approval Safeguards**
   High-value disputes (configurable threshold, default $\ge \$100$) and low-confidence decisions are safely staged behind an approval gate with strict cryptographic state-locking. If a pending human review times out before PayPal's `seller_response_due_date`, the system safely fails closed or takes a pre-configured safe fallback rather than risking default forfeiture or unmonitored LLM actions.
