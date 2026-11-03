/**
 * DisputeSentry AI - Merchant Operator Dashboard Client
 * Handles modal inspection, approval/rejection actions, and 10s auto-refresh.
 */

let activeDisputeId = null;

/**
 * Open dispute modal and fetch full details, evidence, and audit trail via AJAX.
 */
async function openDisputeModal(disputeId) {
    activeDisputeId = disputeId;
    const modal = document.getElementById("dispute-modal");
    if (!modal) return;

    // Reset fields
    document.getElementById("modal-dispute-id").textContent = disputeId;
    document.getElementById("modal-amount").textContent = "Loading...";
    document.getElementById("modal-urgency").textContent = "...";
    document.getElementById("modal-action").textContent = "...";
    document.getElementById("modal-probability").textContent = "...";
    document.getElementById("modal-evidence-status").textContent = "FETCHING";
    document.getElementById("modal-carrier").textContent = "...";
    document.getElementById("modal-tracking").textContent = "...";
    document.getElementById("modal-delivery-status").textContent = "...";
    document.getElementById("modal-shipping-address").textContent = "...";
    document.getElementById("modal-customer-notes").textContent = "Loading notes...";
    document.getElementById("modal-audit-trail").innerHTML = '<div class="text-slate-500 italic">Loading audit trail...</div>';

    modal.classList.remove("hidden");

    try {
        const response = await fetch(`/api/disputes/${encodeURIComponent(disputeId)}`);
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            document.getElementById("modal-customer-notes").textContent = err.detail || "Error loading dispute details";
            return;
        }

        const data = await response.json();

        // Populate dispute summary
        const amountVal = data.dispute_amount?.value != null ? Number(data.dispute_amount.value).toFixed(2) : "0.00";
        const currency = data.dispute_amount?.currency || "USD";
        document.getElementById("modal-amount").textContent = `$${amountVal} ${currency}`;

        const hoursLeft = data.hours_until_due != null ? Number(data.hours_until_due).toFixed(1) : "0.0";
        document.getElementById("modal-urgency").textContent = `${hoursLeft}h`;

        document.getElementById("modal-action").textContent = data.recommended_action || "NONE";
        const prob = data.win_probability != null ? Math.round(Number(data.win_probability) * 100) : 0;
        document.getElementById("modal-probability").textContent = `${prob}%`;

        // Populate evidence package
        const pkg = data.evidence_package || {};
        document.getElementById("modal-evidence-status").textContent = pkg.status || "UNKNOWN";
        document.getElementById("modal-carrier").textContent = pkg.carrier || "-";
        document.getElementById("modal-tracking").textContent = pkg.tracking_number || "-";
        document.getElementById("modal-delivery-status").textContent = pkg.shipment_status || "-";

        if (pkg.order && pkg.order.shipping_address) {
            const addr = pkg.order.shipping_address;
            document.getElementById("modal-shipping-address").textContent = 
                `${addr.line1 || ''}, ${addr.city || ''}, ${addr.state || ''} ${addr.postal_code || ''}, ${addr.country_code || ''}`;
        } else {
            document.getElementById("modal-shipping-address").textContent = "No shipping address on file";
        }

        // Customer notes (safe textContent prevents XSS)
        document.getElementById("modal-customer-notes").textContent = data.customer_notes || "None provided";

        // Audit Trail
        const auditContainer = document.getElementById("modal-audit-trail");
        auditContainer.innerHTML = "";
        const trail = data.audit_trail || [];
        if (trail.length === 0) {
            auditContainer.innerHTML = '<div class="text-slate-500 italic">No audit records yet.</div>';
        } else {
            trail.forEach(entry => {
                const item = document.createElement("div");
                item.className = "p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-xs space-y-1 font-mono";
                
                const header = document.createElement("div");
                header.className = "flex justify-between items-center text-slate-400";
                header.innerHTML = `<span class="text-blue-400 font-semibold">${escapeHtml(entry.action)}</span><span>${escapeHtml(entry.timestamp)}</span>`;
                
                const actorLine = document.createElement("div");
                actorLine.className = "text-slate-400 text-[11px]";
                actorLine.innerHTML = `Actor: <span class="text-slate-200">${escapeHtml(entry.actor || 'system')}</span> &bull; State: <span class="text-emerald-400">${escapeHtml(entry.new_state || entry.action)}</span>`;
                
                const hashLine = document.createElement("div");
                hashLine.className = "text-[10px] text-slate-500 truncate";
                hashLine.textContent = `Hash: ${entry.entry_hash || '-'}`;

                item.appendChild(header);
                item.appendChild(actorLine);
                item.appendChild(hashLine);
                auditContainer.appendChild(item);
            });
        }

        // Configure modal buttons
        const approveBtn = document.getElementById("modal-approve-btn");
        const rejectBtn = document.getElementById("modal-reject-btn");
        if (approveBtn) {
            approveBtn.onclick = () => handleApprove(disputeId);
        }
        if (rejectBtn) {
            rejectBtn.onclick = () => handleReject(disputeId);
        }
    } catch (err) {
        console.error("Failed to load dispute modal:", err);
    }
}

/**
 * Close the detail modal.
 */
function closeModal() {
    const modal = document.getElementById("dispute-modal");
    if (modal) {
        modal.classList.add("hidden");
    }
    activeDisputeId = null;
}

/**
 * Handle Approve action via AJAX POST /api/disputes/{id}/approve
 */
async function handleApprove(disputeId) {
    if (!confirm(`Confirm approval to contest/concede dispute ${disputeId}?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/disputes/${encodeURIComponent(disputeId)}/approve`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                operator_id: "merchant_operator",
                notes: "Approved from UI operator dashboard",
            }),
        });

        if (response.ok) {
            updateBadge(disputeId, "DISPATCHED", "bg-blue-950/80 text-blue-400 border-blue-800");
            closeModal();
            setTimeout(() => window.location.reload(), 500);
        } else {
            const err = await response.json().catch(() => ({}));
            alert(`Approval failed: ${err.detail || 'Server error'}`);
        }
    } catch (err) {
        console.error("Approve request failed:", err);
        alert("Network error processing approval.");
    }
}

/**
 * Handle Reject action via AJAX POST /api/disputes/{id}/reject
 */
async function handleReject(disputeId) {
    const reason = prompt("Enter reason for rejecting recommendation:", "Operator manually cancelled action");
    if (reason === null) return;

    try {
        const response = await fetch(`/api/disputes/${encodeURIComponent(disputeId)}/reject`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                operator_id: "merchant_operator",
                reason: reason || "Manual cancellation",
            }),
        });

        if (response.ok) {
            updateBadge(disputeId, "REJECTED", "bg-red-950/80 text-red-400 border-red-800");
            closeModal();
            setTimeout(() => window.location.reload(), 500);
        } else {
            const err = await response.json().catch(() => ({}));
            alert(`Rejection failed: ${err.detail || 'Server error'}`);
        }
    } catch (err) {
        console.error("Reject request failed:", err);
        alert("Network error processing rejection.");
    }
}

function updateBadge(disputeId, text, classNames) {
    const badge = document.getElementById(`badge-${disputeId}`);
    if (badge) {
        badge.textContent = text;
        badge.className = `px-2.5 py-1 rounded-full text-xs font-semibold ${classNames}`;
    }
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// 10-second polling auto-refresh (only when modal is not actively open)
setInterval(() => {
    const modal = document.getElementById("dispute-modal");
    if (!modal || modal.classList.contains("hidden")) {
        // Poll metrics or refresh quietly
        // window.location.reload();
    }
}, 10000);
