# Seller Protection Decision Matrix

This matrix specifies the deterministic rule conditions evaluated by `app/domain/seller_protection.py` based on official PayPal Seller Protection guidelines for physical goods.

---

## 1. Rule Evaluation Table

| Dispute Reason | Carrier Delivery Status | Tracking Details | Shipped Date vs Dispute Date | Eligibility Result | Recommended Action |
|---|---|---|---|---|---|
| `MERCHANDISE_OR_SERVICE_NOT_RECEIVED` | `DELIVERED` | Matches buyer postal code and country | Prior to dispute open date | `ELIGIBLE` | `CONTEST` ($P_{\text{win}} \ge 0.90$) |
| `MERCHANDISE_OR_SERVICE_NOT_RECEIVED` | `IN_TRANSIT` | Active carrier scan within last 3 days | Prior to dispute open date | `PARTIALLY_ELIGIBLE` | `CONTEST` with tracking notes ($P_{\text{win}} \approx 0.60$) |
| `MERCHANDISE_OR_SERVICE_NOT_RECEIVED` | `PRE_TRANSIT` / Not Shipped | Missing or label created only | No scan | `INELIGIBLE` | `CONCEDE` ($P_{\text{win}} \le 0.05$) |
| `UNAUTHORISED` | Any status | Valid carrier tracking exists | Shipped **before** PayPal dispute/chargeback notification | `ELIGIBLE` | `CONTEST` ($P_{\text{win}} \ge 0.85$) |
| `UNAUTHORISED` | Any status | Valid carrier tracking exists | Shipped **after** PayPal notification | `INELIGIBLE` | `CONCEDE` ($P_{\text{win}} \le 0.05$) |
| `MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED` | `DELIVERED` | Return tracking / refund history | Merchant return policy clearly accepted at checkout | Policy dependent | `CONTEST` or `INQUIRY_OFFER` |
| `MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED` | Any status | Prior full refund executed | `refund_id` exists in merchant store | `ELIGIBLE` (Proof of refund) | `CONTEST` ($P_{\text{win}} \ge 0.95$) |
