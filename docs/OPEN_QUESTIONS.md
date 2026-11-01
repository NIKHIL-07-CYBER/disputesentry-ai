# Open questions

## OQ-001: PayPal dispute fee waiver policy on won disputes
Impact: medium
Why it matters: The decision engine's Net Expected Recovery formula requires knowing whether the $15-$30 dispute fee is reimbursed when the merchant wins under Seller Protection. If non-refundable, low-value disputes have higher hurdle rates to contest.
How to resolve: Run a sandbox dispute under Seller Protection to resolution and verify fee balance adjustments, or consult PayPal Merchant User Agreement section on Dispute Fees.
Status: open (assumption: dispute fee is non-refundable in standard tier, refundable only under verified Seller Protection)
Affects: DSP011, `docs/SPEC.md`, `docs/adr/ADR-001-language-and-stack.md`

## OQ-002: Hackathon live demo hosting persistence requirement
Impact: low
Why it matters: Submission rules mention either local run instructions or a live hosted URL; some entrants note demos must stay live through Dec 15, 2026.
How to resolve: Verify against the official PayPal AI Hackathon Devpost/rules page before final submission.
Status: open (assumption: provide both a containerized local run script and a hosted Fly.io / Render deployment)
Affects: `docs/CI_RELEASE.md`, `docs/ROADMAP.md`

## OQ-003: PayPal MCP Server & Agent Toolkit dispute mutation capabilities
Impact: medium
Why it matters: Research indicates PayPal MCP tools expose `list_disputes` and `get_dispute`, but mutation actions (`provide_evidence`, `accept_claim`) are missing or unverified in the toolkit.
How to resolve: Inspect `@paypal/agent-toolkit` npm package or Python SDK definitions. If absent, use direct PayPal Disputes REST API v1 calls via HTTP client.
Status: open (assumption: use direct PayPal Disputes REST API v1 for all mutations; wrap with MCP-compatible tool schema if exposed to LLM)
Affects: DSP014, DSP015, `docs/adr/ADR-002-integration-strategy.md`

## OQ-004: PayPal multipart evidence file upload vs JSON tracking payload format
Impact: high
Why it matters: The PayPal Disputes API v1 `POST /v1/customer/disputes/{id}/provide-evidence` supports either `multipart/related` (with binary image/PDF attachment parts and JSON metadata) or standard JSON if providing tracking information only. Payload formatting errors lead to 400 Bad Request.
How to resolve: Run PayPal sandbox API test calls against `/v1/customer/disputes/{id}/provide-evidence` with both tracking-only JSON and multipart file payloads.
Status: open (assumption: support dual payload modes: JSON-only for carrier/tracking proof, multipart/form-data with `input` JSON part + binary file parts for documents)
Affects: DSP014, `docs/SPEC.md`, `catalog/fixtures/DSP014/`

## OQ-005: Win rate vs Net Recovery target optimization in automated decision threshold
Impact: medium
Why it matters: Contesting disputes has non-zero labor/risk and dispute fees. Maximizing win rate can decrease net recovery if low-probability, low-value disputes are fought and lost with fee penalties.
How to resolve: Define ROI threshold: `Expected Value = (Win_Probability * Dispute_Amount) - (Loss_Probability * Dispute_Fee) - Overhead_Cost`. If `Expected Value <= 0`, recommend Concede.
Status: open (assumption: default formula applies expected value threshold; threshold and fees are configurable in `config.yaml`)
Affects: DSP011, `docs/SPEC.md`
