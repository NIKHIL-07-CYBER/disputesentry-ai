# Problem statement: DisputeSentry AI

## 1. What is it?
DisputeSentry AI is a service for PayPal merchants. It detects new PayPal disputes, gathers the merchant's own order, shipping and customer-contact records, decides whether to contest or concede each case, and carries out that decision through the PayPal Disputes API. High-value decisions wait for a human, and every action is written to an audit trail. It is being built for the PayPal AI Hackathon, which requires meaningful use of both PayPal (in the free sandbox) and an AI tool [17][18].

## 2. Who is it for, and what pain does it remove?
- Users (proposed default): small and mid-size merchants that sell physical goods through PayPal, plus the finance, operations and support staff who handle their disputes. About one-third of U.S. small businesses report frequently facing chargebacks [29].
- Deadlines: once a case is a claim, the merchant commonly has about 10 days to respond, and silence closes it in the buyer's favor [19][20]. Other guides give 20 days for an initial information request and 10 days after a chargeback notice [21]. The per-case deadline is the `seller_response_due_date` field [2]. Pre-chargeback alerts allow 20 hours to refund and avoid the chargeback [1].
- Cost: one guide lists a $15 standard dispute fee, a $30 high-volume fee and a $20 chargeback fee [22]. Sources disagree on whether fees are waived or refunded when the merchant wins or has Seller Protection (to verify) [22][23].
- Low engagement: win rates on contested cases look good, but net recovery across all disputes is much lower [26][25]. Smaller merchants report low win rates more often than larger ones [27]. Contesting has fixed costs, so low-value disputes can cost more to fight than to concede [28].
- How they cope today: the manual Resolution Center, the Disputes API for custom automation [1], paid vendors [30][31], or accepting the loss.

## 3. Core capabilities (most important first)
1. Receive PayPal dispute webhooks (created, updated, resolved), verify their signatures and ignore duplicates [6][7][11].
2. Fetch each dispute's details: reason, status, lifecycle stage, requested evidence, response deadline, allowed response options and action links [2].
3. Look up the merchant's matching records: order, carrier and tracking, delivery confirmation, refunds, customer messages. In v1 these come from a seeded data store (proposed default).
4. Decide per case: contest with evidence, concede, or (in the inquiry stage) message or make an offer. Each decision states its reasoning, the evidence it relies on and an estimated chance of winning. Inputs are PayPal's evidence requirements per reason [9] and Seller Protection rules [10].
5. Execute through the Disputes API (provide evidence, accept claim, make offer, send message), only where the dispute's links and allowed options permit it [2][4][5].
6. Approval gate: act automatically below a value threshold and ask a human above it (proposed default) [38][39].
7. Show a dashboard of disputes ranked by deadline and amount at risk, with the decision, reasoning and audit log for each.

## 4. Form factor (how people install or reach it)
- Proposed default: a hosted web app with a public webhook endpoint and a dashboard, plus repository instructions to run it locally.
- The hackathon accepts either full run instructions or a hosted demo [18][42] (to verify against the official rules page). One entrant's notes say the demo must stay live through Dec 15 (to verify).

## 5. Inputs and outputs
- In: dispute webhook JSON (dispute ID, reason, status, amount, outcome) [7]; dispute details JSON [2]; merchant records (format not set by research; seeded data in v1); evidence files in JPG, JPEG, GIF, PNG or PDF, each under 10 MB and up to 50 MB per call [8].
- Out to PayPal: provide-evidence requests with an evidence type, tracking info or refund IDs, notes and files [2][5]; accept-claim, make-offer and send-message calls with notes [2].
- Out to people: a decision record (action, reason, evidence used, win estimate, expected cost) and a deadline-ordered dashboard (proposed default).

## 6. Systems it touches
- PayPal Disputes API v1: list and show disputes, provide evidence, accept claim, make offer, escalate, appeal, send message, provide supporting info [2][4].
- Dispute model: internal disputes start in the PayPal Resolution Center and can pass through an inquiry stage, then become claims. External disputes arrive from a bank as chargebacks, where PayPal only relays information [1]. Stages are INQUIRY, CHARGEBACK, PRE_ARBITRATION and ARBITRATION, and statuses include WAITING_FOR_SELLER_RESPONSE [2]. The inquiry stage applies only to internal item-not-received and not-as-described cases, and lasts up to 20 days [2].
- Evidence is requested by reason (not received, not as described, unauthorised) and typed PROOF_OF_FULFILLMENT, PROOF_OF_REFUND or OTHER [9][2]. Evidence can be sent only when the dispute shows a provide-evidence link [5]. The PayPal sample uses a multipart request with a JSON `input` part and file parts [2].
- Accepting a claim closes the case for the buyer and PayPal refunds from the merchant's account [4].
- Sandbox testing: buyer-side credentials are needed to create test disputes. Sandbox-only endpoints create disputes, settle them, change reasons and create chargebacks [3]. Test transactions are made by sending money from a sandbox personal account to the business account [3].
- Webhooks: signature verification uses PayPal's verification endpoint or local certificate checks [11][12]. The webhook ID is per environment, and simulated events cannot be verified [12][13].
- Auth: OAuth 2.0 client credentials. The token response reports `expires_in`, and the app requests a new token after expiry [14].
- PayPal's MCP server and Agent Toolkit expose dispute list and get tools. I found no dispute evidence or accept-claim tools there (to verify), so those calls likely need the REST API [15][16].
- Seller Protection: physical goods generally need proof of shipment or delivery to the transaction's address, and PayPal decides eligibility at its discretion. Intangible goods have extra requirements [10].

## 7. Quality bar
- Correctness (proposed default): only evidence that exists in the merchant's records may be submitted. Evidence must fit the dispute reason [9]. For delivery proof, PayPal expects a verifiable tracking number, delivery date and status, and an address match [10].
- Deadlines: a missed deadline loses the case [19], so the deadline logic must be tested.
- Reliability: signature verification, duplicate handling and token refresh [11][14].
- Oversight: classify actions by risk, escalate by amount, log every proposal, approval and result, and tie approvals to the state a human actually reviewed [38][39]. An approval that times out should deny the action [39].
- Privacy and security: keep card numbers and sensitive authentication data out of prompts, logs and evidence [40][41]. Customer text is untrusted input, since crafted inputs can steer an agent that has payment access [41].
- Measurement: track net recovery as well as win rate, since the two diverge widely [26].
- Speed: a decision well inside the response window (proposed default; no source gives a number).

## 8. Constraints
- Deadline: Nov 12, 2026, 12:00 PM Pacific, which is 1:30 AM IST on Nov 13 [17][18]. From Nov 1 that leaves about 11 days.
- Sandbox only, no real money [17][42]. Individual or team entries are allowed, and existing projects qualify with meaningful progress in the period [42].
- Submission (to verify, official rules page could not be fetched): working demo, public repository with a detectable open-source license, public YouTube video under 3 minutes. A mockup does not qualify [18][42].
- Judging criteria: technical implementation, design, potential impact, innovation and presentation [43].
- Tech stack is not chosen. PayPal's toolkit supports TypeScript and Python (proposed default) [15]. Sponsor tools such as AG Grid or Elastic are optional [17].

## 9. Non-goals (what version 1 will not do)
All are proposed defaults.
- No live production money or real merchant accounts.
- No other processors (Stripe, Shopify Payments) and no pre-dispute alert networks.
- No model trained on real outcome data. Win estimates are explained heuristics, not statistics.
- No appeals, pre-arbitration or arbitration handling beyond showing the case.
- No legal or compliance advice.
- No auto-refund or auto-concede above the approval threshold without a human.

## 10. Reference material
- PayPal Resolution Center (manual) and Disputes API (building block) [1][2].
- Chargeflow: closed SaaS with a public API. Disputes carry a `source` field including PayPal, and Chargeflow assembles and submits the evidence [30]. Pricing and automation claims are vendor claims [31][32].
- Justt: enterprise automation, says it applies ROI logic to choose which disputes to fight (vendor claim, to verify), pricing not public [31].
- Chargebacks911: described as semi-automated and costly by a rival (to verify) [32][31].
- Disputifier: automation for PayPal and other processors with results-based pricing (vendor claim, to verify) [37].
- Stripe Smart Disputes: AI rules engine that builds and submits evidence, Stripe only [33].
- AgentGuard CB: open source, Stripe, deterministic evidence payloads staged for human review, no LLM narratives [34].
- disputeguard: open-source evidence checker for Visa reason codes, v0.1.0 [35].
- openclaudia stripe-dispute skill: MIT, Stripe, shows evidence and a win assessment for approval before submitting [36].
- Gap (to verify): I found no open-source tool that decides contest versus concede for PayPal's Disputes API.

## 11. Success looks like
All are proposed defaults.
- A judge can run or open the project and watch a real sandbox dispute go from webhook to decision to PayPal action to confirmed state, then see the resolved event [3][6].
- At least one dispute per main reason (not received, unauthorised, not as described) is handled in the sandbox [3][9].
- On a seeded set with known intended outcomes, the contest/concede choice matches the expected one (target to be set by the team).
- No call outside a dispute's allowed options, and no missed deadline on the demo queue [2].
- Every action has an audit record, and above-threshold cases wait for approval [38][39].
- The dashboard reports win rate and net recovery [26].
- The demo video runs under 3 minutes [18].

## Sources
Accessed 2026-11-01.
1. PayPal Developer, Disputes overview: https://developer.paypal.com/disputes/overview
2. PayPal Developer, Use Disputes API: https://developer.paypal.com/platforms/disputes/handle-disputes/use-disputes-api
3. PayPal Developer, Disputes test and go live: https://developer.paypal.com/disputes/test-go-live.md
4. PayPal docs, Accept claim: https://docs.paypal.ai/reference/api/rest/disputes-actions/accept-claim.md
5. PayPal docs, Provide evidence: https://docs.paypal.ai/reference/api/rest/disputes-actions/provide-evidence.md
6. PayPal docs, Disputes v1 webhook events: https://docs.paypal.ai/reference/webhook-events/disputes-v1
7. PayPal Developer, Subscribe to disputes webhooks: https://developer.paypal.com/docs/disputes/webhooks
8. PayPal docs, Supported file types and sizes: https://docs.paypal.ai/growth/disputes/reference/supported-file-types-sizes.md
9. PayPal docs, Dispute reasons and evidence: https://docs.paypal.ai/growth/disputes/reference/dispute-reasons.md
10. PayPal, Seller Protection: https://www.paypal.com/us/webapps/mpp/ua/seller-protection
11. PayPal docs, Verify webhook signature: https://docs.paypal.ai/reference/api/rest/verify-webhook-signature/verify-webhook-signature
12. PayPal Developer, Webhooks: https://developer.paypal.com/api/rest/webhooks/rest
13. PayPal Developer, Invoicing troubleshooting: https://developer.paypal.com/invoicing/troubleshooting.md
14. PayPal Developer, Get started with REST APIs: https://developer.paypal.com/api/get-started
15. PayPal Developer, Agent toolkit: https://developer.paypal.com/tools/agent-toolkit
16. Google ADK, PayPal MCP tool: https://google.github.io/adk-docs/integrations/paypal
17. PayPal Community Blog, Hackathon announcement: https://developer.paypal.com/community/blog/PayPal_AI_Hackathon
18. The GenAI Magazine, PayPal AI Hackathon 2026: https://thegenaimagazine.com/paypal-ai-hackathon-2026-ideas-deadline-prizes
19. Chargeback.io, PayPal chargeback time limits: https://www.chargeback.io/blog/paypal-chargeback-time-limits-guide
20. Chargebacks911, PayPal chargeback time limits: https://chargebacks911.com/paypal-chargeback-time-limits/
21. Adyen, PayPal chargebacks: https://docs.adyen.com/risk-management/chargeback-guidelines/paypal-chargebacks
22. Chargeback Gurus, PayPal chargebacks guide: https://www.chargebackgurus.com/blog/a-merchants-guide-to-paypal-credit-card-chargebacks
23. Chargeflow, PayPal chargeback: https://www.chargeflow.io/chargebacks-101/paypal-chargeback
24. Chargeback.io, Chargeback statistics 2026: https://www.chargeback.io/fr/blog/chargeback-statistics
25. Crowdfund Insider, 2024 Chargeback Field Report: https://www.crowdfundinsider.com/2024/12/234590-nearly-half-of-chargebacks-stem-from-misuse-or-outright-abuse-report/
26. VersaPay, win rate vs net recovery: https://www.versapay.com/resources/two-dispute-management-kpis-chargeback-strategy
27. Kount, representment engagement: https://kount.com/en-gb/node/106
28. PXP, Chargeback representment: https://www.pxp.io/payments-glossary/chargeback-representment
29. PYMNTS, Time spent managing disputes: https://www.pymnts.com/?p=2274130
30. Chargeflow docs, Automate a chargeback dispute: https://docs.chargeflow.io/docs/merchants/automation/automate-a-chargeback-dispute.md
31. Justt, Justt vs Chargebacks911: https://justt.ai/comparisons/justt-vs-chargebacks911/
32. Chargeflow, llms.txt: https://www.chargeflow.io/es/llms.txt
33. Stripe docs, Smart Disputes: https://docs.stripe.com/disputes/get-started/smart-disputes
34. MerchantGuard, agentguard-cb: https://github.com/MerchantGuard/agentguard-cb
35. PyPI, disputeguard: https://pypi.org/project/disputeguard/
36. Skillselion, stripe-dispute skill: https://skillselion.com/skills/openclaudia/openclaudia-skills/stripe-dispute
37. Disputifier, PayPal chargeback: https://www.disputifier.com/post/paypal-chargeback
38. Prometeo, Human-in-the-loop agentic banking: https://prometeoapi.com/en/blog/human-in-the-loop-agentic-banking
39. DZone, Human-in-the-loop approval gates: https://dzone.com/articles/human-in-the-loop-approval-enterprise-ai-agents
40. Gravitee, PCI DSS for LLM payment flows: https://gravitee.io/corpus/gen-1318/merchant-account-provider/pci-dss-compliance-considerations-for-llm-enabled-payment-flows-and-merchant-account-integrations.html
41. Polygraf AI, PCI-DSS and AI tools: https://www.polygraf.ai/blogposts/pci-dss-and-ai-tools/
42. DevGrants Daily, PayPal AI Hackathon 2026: https://devgrantsdaily.com/items/2026-10-02-paypal-ai-hackathon-2026/
43. Internshala, PayPal AI Hackathon 2026: https://internshala.com/competitions/?p=13021
