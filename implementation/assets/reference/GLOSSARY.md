# Domain and Technical Glossary

| Term | Definition |
|---|---|
| **Dispute** | Any disagreement initiated by a buyer regarding a PayPal transaction, spanning inquiries, claims, and external chargebacks. |
| **Inquiry** | The initial internal stage for Item Not Received or Not As Described disputes. Allows mutual messaging and settlement offers between buyer and seller for up to 20 days. |
| **Claim** | An escalated dispute where PayPal is asked to intervene and decide the financial outcome based on evidence submitted by both parties. |
| **Chargeback** | An external dispute filed by a cardholder directly with their card issuer (bank). PayPal acts as an intermediary relaying merchant evidence. |
| **Seller Protection** | A PayPal program protecting merchants from losing funds on eligible transactions for Item Not Received or Unauthorised Payment disputes. |
| **Proof of Delivery (POD)** | Carrier online tracking showing delivered status, delivery date, and recipient postal code / address matching the transaction. |
| **Proof of Shipment (POS)** | Online documentation showing item was shipped before an Unauthorised dispute was reported. |
| **HATEOAS** | Hypermedia As The Engine Of Application State. PayPal Disputes API embeds allowed actions (`rel="provide_evidence"`) in the dispute's `links` array. |
| **PAN** | Primary Account Number. The 13 to 19 digit credit or debit card number. Subject to strict zero-storage PCI DSS 3.4 rules. |
| **Net Expected Recovery ($\text{EV}$)** | The mathematical expectation of net financial gain from contesting a dispute, factoring win probability, amount, fees, and overhead. |
| **Fail-Safe Fallback** | Automatic submission of defensive evidence package when time until deadline is $\le 2\text{ hours}$ to prevent default loss. |
