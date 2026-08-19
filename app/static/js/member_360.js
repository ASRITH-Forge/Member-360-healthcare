/**
 * Member 360° Health Intelligence Assistant
 * Enterprise Client-Side Interactive Controller
 */
document.addEventListener("DOMContentLoaded", () => {
  // Mobile Navigation Menu Toggle Controller
  const mobileNavToggle = document.getElementById("mobileNavToggle");
  const headerNav = document.getElementById("headerNav");

  if (mobileNavToggle && headerNav) {
    mobileNavToggle.addEventListener("click", (e) => {
      e.stopPropagation();
      const isExpanded = mobileNavToggle.getAttribute("aria-expanded") === "true";
      mobileNavToggle.setAttribute("aria-expanded", String(!isExpanded));
      mobileNavToggle.classList.toggle("open");
      headerNav.classList.toggle("open");
    });

    // Close menu when clicking outside
    document.addEventListener("click", (e) => {
      if (!headerNav.contains(e.target) && !mobileNavToggle.contains(e.target) && headerNav.classList.contains("open")) {
        mobileNavToggle.setAttribute("aria-expanded", "false");
        mobileNavToggle.classList.remove("open");
        headerNav.classList.remove("open");
      }
    });

    // Close mobile menu on Escape key
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && headerNav.classList.contains("open")) {
        mobileNavToggle.setAttribute("aria-expanded", "false");
        mobileNavToggle.classList.remove("open");
        headerNav.classList.remove("open");
      }
    });

    // Close mobile menu on breakpoint resize to desktop
    window.addEventListener("resize", () => {
      if (window.innerWidth > 768 && headerNav.classList.contains("open")) {
        mobileNavToggle.setAttribute("aria-expanded", "false");
        mobileNavToggle.classList.remove("open");
        headerNav.classList.remove("open");
      }
    });
  }

  // Tab Switching Controller with Touch-Friendly Scroll
  const tabButtons = document.querySelectorAll(".tab-nav-btn, .tab-btn");
  const tabPanes = document.querySelectorAll(".tab-content-pane, .tab-pane");

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");
      if (!targetTab) return;

      tabButtons.forEach((b) => b.classList.remove("active"));
      tabPanes.forEach((p) => p.classList.remove("active"));

      btn.classList.add("active");
      const targetPane = document.getElementById(`tab-${targetTab}`);
      if (targetPane) {
        targetPane.classList.add("active");
      }

      // Smoothly bring the active tab into center view on mobile/horizontal scroll
      btn.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
    });
  });

  // Global Source Traceability Modal
  const modalOverlay = document.getElementById("sourceModal");
  const modalCloseBtn = document.getElementById("closeModalBtn");
  const modalContent = document.getElementById("sourceModalContent");
  const modalTitle = document.getElementById("sourceModalTitle");

  const FIELD_LABELS = {
    member_id: "Member ID",
    first_name: "First Name",
    last_name: "Last Name",
    date_of_birth: "Date of Birth",
    gender: "Gender",
    city: "City",
    state: "State",
    zip: "Postal Code",
    postal_code: "Postal Code",
    is_alive: "Living Status",
    death_date: "Date of Death",
    healthcare_expenses: "Total Healthcare Expenses",
    healthcare_coverage: "Coverage Amount Paid",
    eligibility_id: "Eligibility Record ID",
    payer_name: "Payer Organization",
    plan_name: "Health Plan Name",
    ownership: "Ownership Type",
    coverage_start: "Coverage Start Date",
    coverage_end: "Coverage End Date",
    effective_date: "Effective Date",
    termination_date: "Termination Date",
    claim_id: "Claim ID",
    claim_date: "Service / Claim Date",
    claim_type: "Claim Type",
    provider: "Healthcare Provider",
    procedure: "Procedure / Service",
    amount: "Total Billed Amount",
    payer_coverage: "Payer Coverage Paid",
    member_copay: "Member Copay",
    medication_id: "Medication Record ID",
    medication_name: "Medication Name",
    code: "RxNorm Code",
    start_date: "Prescription Start Date",
    end_date: "Prescription End Date",
    reason: "Documented Clinical Reason",
    total_cost: "Total Medication Cost",
    gap_id: "Care Gap ID",
    gap_type: "Care Gap Standard",
    description: "Clinical Gap Description",
    detected_date: "Detection Timestamp",
    due_date: "Target / Due Date",
    authorization_id: "Authorization ID",
    service: "Requested Clinical Service",
    request_date: "Request Submission Date",
    decision_date: "Determination Date",
    notes: "Clinical / Operational Notes",
    interaction_id: "Interaction ID",
    interaction_date: "Interaction Timestamp",
    channel: "Contact Channel",
    reason: "Documented Reason",
    reason_for_contact: "Contact Reason",
    summary: "Representative Summary",
    status: "Record Status",
    request_id: "Request ID",
    organization_id: "Organization ID",
    organization_name: "Organization Name",
    request_type: "Request Type",
    service: "Requested Service / Procedure",
    priority: "Priority Level",
    request_date: "Request Submission Date",
    due_date: "Target Due Date",
    resolution_notes: "Resolution / Action Notes",
    requested_by: "Submitted By",
    assigned_to: "Assigned Coordinator",
    created_at: "Creation Timestamp",
    updated_at: "Last Updated Timestamp",
    source: "Data Source",
    _id: "Database Object Identifier"
  };

  /**
   * Reusable helper to determine whether a data value represents unavailable/empty information.
   * Handles null, undefined, NaN, empty strings, and unavailable keywords case-insensitively.
   */
  function isUnavailableValue(val) {
    if (val === null || val === undefined) return true;
    if (typeof val === "number") {
      return isNaN(val) || !isFinite(val);
    }
    if (typeof val === "string") {
      const trimmed = val.trim().toLowerCase();
      const emptyKeywords = [
        "",
        "none",
        "null",
        "nan",
        "undefined",
        "not recorded",
        "not available",
        "unknown",
        "n/a",
        "na"
      ];
      return emptyKeywords.includes(trimmed);
    }
    return false;
  }

  function formatFieldName(key) {
    if (FIELD_LABELS[key]) return FIELD_LABELS[key];
    return key
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  }

  function formatINR(val) {
    if (isUnavailableValue(val)) {
      return "₹0.00";
    }
    const num = Number(val);
    const isNeg = num < 0;
    const absNum = Math.abs(num);
    const parts = absNum.toFixed(2).split(".");
    let intPart = parts[0];
    const decPart = parts[1];

    if (intPart.length > 3) {
      const last3 = intPart.substring(intPart.length - 3);
      let rest = intPart.substring(0, intPart.length - 3);
      const groups = [];
      while (rest.length > 2) {
        groups.unshift(rest.substring(rest.length - 2));
        rest = rest.substring(0, rest.length - 2);
      }
      if (rest.length > 0) {
        groups.unshift(rest);
      }
      intPart = groups.join(",") + "," + last3;
    }
    return `₹${isNeg ? "-" : ""}${intPart}.${decPart}`;
  }

  function formatFieldValue(key, val) {
    if (typeof val === "boolean") {
      return val
        ? `<span class="badge badge-active">True</span>`
        : `<span class="badge badge-denied">False</span>`;
    }
    if (typeof val === "number" && (key.includes("expense") || key.includes("coverage") || key.includes("amount") || key.includes("copay") || key.includes("cost"))) {
      return formatINR(val);
    }
    return escapeHtml(String(val));
  }

  function openSourceModal(sourceType, sourceId) {
    if (!modalOverlay || !modalContent) return;

    if (modalTitle) {
      modalTitle.innerHTML = `<span>Source Record: <strong>${escapeHtml(sourceType)}</strong> [${escapeHtml(sourceId)}]</span>`;
    }
    modalContent.innerHTML = `
      <div style="text-align: center; padding: 2.5rem; color: #64748b;">
        <span class="spinner spinner-dark" style="margin-right: 0.5rem;"></span>
        Retrieving verified record from database...
      </div>
    `;
    modalOverlay.classList.add("active");
    document.body.style.overflow = "hidden";

    fetch(`/api/ai/source/${encodeURIComponent(sourceType)}/${encodeURIComponent(sourceId)}`)
      .then((res) => {
        if (res.status === 401) {
          window.location.href = "/login";
          throw new Error("Authentication required. Redirecting to login...");
        }
        if (!res.ok) throw new Error("Source record not found in system database.");
        return res.json();
      })
      .then((data) => {
        if (data.record) {
          let html = `
            <div class="verified-badge">
              <span>✓ Verified Database Source Record</span>
            </div>
            <table class="source-kv-table">
              <tbody>
          `;
          let renderedCount = 0;
          for (const [k, v] of Object.entries(data.record)) {
            if (k === "_id") continue; // Omit internal mongo object id
            if (isUnavailableValue(v)) continue; // Omit unavailable/empty fields from UI display

            renderedCount++;
            html += `
              <tr>
                <th>${escapeHtml(formatFieldName(k))}</th>
                <td>${formatFieldValue(k, v)}</td>
              </tr>
            `;
          }
          if (renderedCount === 0) {
            html += `<tr><td colspan="2" style="text-align: center; color: #64748b;">No optional details documented in this record.</td></tr>`;
          }
          html += `
              </tbody>
            </table>
          `;
          modalContent.innerHTML = html;
        } else {
          modalContent.innerHTML = `<div style="color: #991b1b; padding: 1rem; background: #fef2f2; border-radius: 4px;">Record data is empty or could not be verified.</div>`;
        }
      })
      .catch((err) => {
        modalContent.innerHTML = `
          <div style="color: #991b1b; padding: 1rem; background: #fef2f2; border: 1px solid #fecaca; border-radius: 4px;">
            <strong>Lookup Error:</strong> ${escapeHtml(err.message)}
          </div>
        `;
      });
  }

  function closeModal() {
    if (modalOverlay) {
      modalOverlay.classList.remove("active");
      document.body.style.overflow = "";
    }
  }

  if (modalCloseBtn) {
    modalCloseBtn.addEventListener("click", closeModal);
  }

  if (modalOverlay) {
    modalOverlay.addEventListener("click", (e) => {
      if (e.target === modalOverlay) closeModal();
    });
  }

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modalOverlay && modalOverlay.classList.contains("active")) {
      closeModal();
    }
  });

  // Delegated Click Listener for Source Traceability Chips
  document.addEventListener("click", (e) => {
    const chip = e.target.closest(".source-chip");
    if (chip) {
      const sType = chip.getAttribute("data-source-type");
      const sId = chip.getAttribute("data-source-id");
      if (sType && sId) {
        openSourceModal(sType, sId);
      }
    }
  });

  // AI Summary Generator Controller
  const btnGenerateAi = document.getElementById("btnGenerateAi");
  const aiResultsContainer = document.getElementById("aiResultsContainer");
  const aiStatusMsg = document.getElementById("aiStatusMsg");
  const aiStatusText = document.getElementById("aiStatusText");

  if (btnGenerateAi) {
    btnGenerateAi.addEventListener("click", async () => {
      const memberId = btnGenerateAi.getAttribute("data-member-id");
      if (!memberId) return;

      btnGenerateAi.disabled = true;
      btnGenerateAi.innerHTML = `<span class="spinner" style="border-color: rgba(255,255,255,0.3); border-top-color: #fff;"></span> Analyzing...`;
      
      if (aiStatusMsg) {
        aiStatusMsg.style.display = "flex";
        if (aiStatusText) {
          aiStatusText.textContent = "AI is synthesizing clinical facts and validating source traceability with Gemini...";
        }
      }

      try {
        const res = await fetch(`/api/ai/member/${encodeURIComponent(memberId)}/summary`, {
          method: "POST",
          headers: { "Content-Type": "application/json" }
        });

        if (res.status === 401) {
          window.location.href = "/login";
          throw new Error("Authentication required. Redirecting to login...");
        }

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail?.message || errData.detail || "Failed to generate AI summary.");
        }

        const data = await res.json();
        renderAiSummary(data);
      } catch (err) {
        if (aiResultsContainer) {
          aiResultsContainer.innerHTML = `
            <div style="background: #fef2f2; border: 1px solid #fecaca; padding: 1rem 1.25rem; border-radius: 6px; color: #991b1b; font-size: 0.875rem;">
              <strong>Synthesis Error:</strong> ${escapeHtml(err.message)}
            </div>
          `;
        }
      } finally {
        btnGenerateAi.disabled = false;
        btnGenerateAi.innerHTML = `Re-Generate AI Summary`;
        if (aiStatusMsg) aiStatusMsg.style.display = "none";
      }
    });
  }

  function renderAiSummary(data) {
    if (!aiResultsContainer) return;

    let factsHtml = "";
    if (data.key_facts && data.key_facts.length > 0) {
      factsHtml = data.key_facts
        .filter((f) => f && !isUnavailableValue(f.text))
        .map(
          (f) => `
        <li class="ai-fact-item">
          <div class="ai-fact-text">${escapeHtml(f.text)}</div>
          <button class="source-chip" data-source-type="${escapeHtml(f.source_type)}" data-source-id="${escapeHtml(f.source_id)}">
            Source: ${escapeHtml(f.source_type)} [${escapeHtml(f.source_id)}] &bull; Inspect
          </button>
        </li>
      `
        )
        .join("");
    }
    if (!factsHtml) {
      factsHtml = `<li class="ai-fact-item" style="color: #64748b; font-style: italic;">No specific factual statements extracted.</li>`;
    }

    let issuesHtml = "";
    if (data.open_issues && data.open_issues.length > 0) {
      issuesHtml = data.open_issues
        .filter((iss) => iss && !isUnavailableValue(iss.text))
        .map(
          (iss) => `
        <li class="ai-fact-item item-issue">
          <div class="ai-fact-text">
            <span class="badge ${iss.urgency === 'High' ? 'badge-urgent' : 'badge-pending'}" style="font-size: 0.65rem; margin-bottom: 0.25rem;">
              ${escapeHtml(iss.urgency || "Operational")}
            </span>
            <div>${escapeHtml(iss.text)}</div>
          </div>
          <button class="source-chip" data-source-type="${escapeHtml(iss.source_type)}" data-source-id="${escapeHtml(iss.source_id)}">
            Source: ${escapeHtml(iss.source_type)} [${escapeHtml(iss.source_id)}] &bull; Inspect
          </button>
        </li>
      `
        )
        .join("");
    }
    if (!issuesHtml) {
      issuesHtml = `<li class="ai-fact-item" style="color: #047857;">✓ No active open issues documented in records.</li>`;
    }

    let actionsHtml = "";
    if (data.next_actions && data.next_actions.length > 0) {
      actionsHtml = data.next_actions
        .filter((act) => act && !isUnavailableValue(act.text))
        .map(
          (act) => `
        <li class="ai-fact-item item-action">
          <div class="ai-fact-text">
            <span class="badge badge-active" style="font-size: 0.65rem; margin-bottom: 0.25rem;">
              ${escapeHtml(act.action_type || "Follow-up")}
            </span>
            <div>${escapeHtml(act.text)}</div>
          </div>
          <button class="source-chip" data-source-type="${escapeHtml(act.source_type)}" data-source-id="${escapeHtml(act.source_id)}">
            Source: ${escapeHtml(act.source_type)} [${escapeHtml(act.source_id)}] &bull; Inspect
          </button>
        </li>
      `
        )
        .join("");
    }
    if (!actionsHtml) {
      actionsHtml = `<li class="ai-fact-item" style="color: #64748b; font-style: italic;">No operational follow-up actions required.</li>`;
    }

    aiResultsContainer.innerHTML = `
      <div class="ai-synthesis-columns">
        <div class="ai-column-box">
          <div class="ai-column-title">
            <span>Key Member Facts</span>
            <span class="tab-count-pill">${data.key_facts ? data.key_facts.length : 0}</span>
          </div>
          <ul class="ai-facts-list">${factsHtml}</ul>
        </div>
        <div class="ai-column-box">
          <div class="ai-column-title">
            <span>Documented Open Issues</span>
            <span class="tab-count-pill">${data.open_issues ? data.open_issues.length : 0}</span>
          </div>
          <ul class="ai-facts-list">${issuesHtml}</ul>
        </div>
        <div class="ai-column-box">
          <div class="ai-column-title">
            <span>Suggested Next Operational Actions</span>
            <span class="tab-count-pill">${data.next_actions ? data.next_actions.length : 0}</span>
          </div>
          <ul class="ai-facts-list">${actionsHtml}</ul>
        </div>
      </div>
      <div class="ai-disclaimer-bar">
        <span><em>Operational Disclaimer:</em> ${escapeHtml(data.disclaimer || "AI-generated guidance for representative review.")}</span>
        <span>Generated: ${escapeHtml(data.generated_at || new Date().toISOString())}</span>
      </div>
    `;
  }

  // =========================================================================
  // Submit Organization Request Modal Controller
  // =========================================================================
  const submitRequestModal = document.getElementById("submitRequestModal");
  const closeSubmitRequestModalBtn = document.getElementById("closeSubmitRequestModalBtn");
  const btnCancelSubmitRequest = document.getElementById("btnCancelSubmitRequest");
  const submitRequestForm = document.getElementById("submitRequestForm");
  const submitRequestFeedback = document.getElementById("submitRequestFeedback");
  const reqMemberIdInput = document.getElementById("reqMemberId");
  const reqDateInput = document.getElementById("reqDate");

  function openSubmitRequestModal(memberId = "") {
    if (!submitRequestModal) return;
    if (submitRequestFeedback) {
      submitRequestFeedback.style.display = "none";
      submitRequestFeedback.innerHTML = "";
    }
    if (submitRequestForm) {
      submitRequestForm.reset();
    }
    if (reqMemberIdInput && memberId) {
      reqMemberIdInput.value = memberId;
    }
    if (reqDateInput) {
      reqDateInput.value = new Date().toISOString().split("T")[0];
    }
    submitRequestModal.classList.add("active");
    document.body.style.overflow = "hidden";
  }

  function closeSubmitRequestModal() {
    if (submitRequestModal) {
      submitRequestModal.classList.remove("active");
      document.body.style.overflow = "";
    }
  }

  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".btn-open-submit-modal");
    if (btn) {
      const memberId = btn.getAttribute("data-member-id") || "";
      openSubmitRequestModal(memberId);
    }
  });

  if (closeSubmitRequestModalBtn) {
    closeSubmitRequestModalBtn.addEventListener("click", closeSubmitRequestModal);
  }
  if (btnCancelSubmitRequest) {
    btnCancelSubmitRequest.addEventListener("click", closeSubmitRequestModal);
  }
  if (submitRequestModal) {
    submitRequestModal.addEventListener("click", (e) => {
      if (e.target === submitRequestModal) closeSubmitRequestModal();
    });
  }

  if (submitRequestForm) {
    submitRequestForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btnSubmit = document.getElementById("btnSubmitRequest");
      if (btnSubmit) {
        btnSubmit.disabled = true;
        btnSubmit.innerHTML = `<span class="spinner spinner-dark" style="margin-right: 0.4rem;"></span> Submitting...`;
      }

      const formData = new FormData(submitRequestForm);
      const payload = {
        organization_name: formData.get("organization_name") || "",
        organization_id: formData.get("organization_id") || "",
        member_id: formData.get("member_id") || "",
        request_type: formData.get("request_type") || "",
        service: formData.get("service") || "",
        priority: formData.get("priority") || "Medium",
        request_date: formData.get("request_date") || "",
        due_date: formData.get("due_date") || "",
        requested_by: formData.get("requested_by") || "",
        description: formData.get("description") || ""
      };

      try {
        const res = await fetch("/api/requests", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (res.status === 401) {
          window.location.href = "/login";
          throw new Error("Authentication required. Redirecting to login...");
        }

        const data = await res.json();

        if (!res.ok) {
          throw new Error(data.detail?.message || data.detail || "Failed to submit request.");
        }

        if (submitRequestFeedback) {
          submitRequestFeedback.style.display = "block";
          submitRequestFeedback.innerHTML = `
            <div style="background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; padding: 0.75rem 1rem; border-radius: 6px; font-size: 0.875rem;">
              <strong>Success:</strong> Request ${escapeHtml(data.request_id || "submitted")} submitted successfully.
            </div>
          `;
        }

        submitRequestForm.reset();

        // Reload page smoothly after brief delay to show updated data
        setTimeout(() => {
          closeSubmitRequestModal();
          window.location.reload();
        }, 1200);
      } catch (err) {
        if (submitRequestFeedback) {
          submitRequestFeedback.style.display = "block";
          submitRequestFeedback.innerHTML = `
            <div style="background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; padding: 0.75rem 1rem; border-radius: 6px; font-size: 0.875rem;">
              <strong>Error:</strong> ${escapeHtml(err.message)}
            </div>
          `;
        }
      } finally {
        if (btnSubmit) {
          btnSubmit.disabled = false;
          btnSubmit.innerHTML = `Submit Request`;
        }
      }
    });
  }

  // =========================================================================
  // Update Request Status Modal Controller (Care Coordinator)
  // =========================================================================
  const updateStatusModal = document.getElementById("updateStatusModal");
  const closeUpdateStatusModalBtn = document.getElementById("closeUpdateStatusModalBtn");
  const btnCancelUpdateStatus = document.getElementById("btnCancelUpdateStatus");
  const updateStatusForm = document.getElementById("updateStatusForm");
  const updateStatusFeedback = document.getElementById("updateStatusFeedback");

  function openUpdateStatusModal(btn) {
    if (!updateStatusModal) return;
    if (updateStatusFeedback) {
      updateStatusFeedback.style.display = "none";
      updateStatusFeedback.innerHTML = "";
    }

    const reqId = btn.getAttribute("data-request-id") || "";
    const org = btn.getAttribute("data-org") || "";
    const service = btn.getAttribute("data-service") || "";
    const currentStatus = btn.getAttribute("data-status") || "Pending";
    const priority = btn.getAttribute("data-priority") || "Medium";
    const assigned = btn.getAttribute("data-assigned") || "";
    const due = btn.getAttribute("data-due") || "";
    const notes = btn.getAttribute("data-notes") || "";

    const editReqIdInput = document.getElementById("editRequestId");
    const displayReqId = document.getElementById("displayEditRequestId");
    const displayOrgService = document.getElementById("displayEditOrgService");
    const editStatusSelect = document.getElementById("editStatus");
    const editPrioritySelect = document.getElementById("editPriority");
    const editAssignedToInput = document.getElementById("editAssignedTo");
    const editDueDateInput = document.getElementById("editDueDate");
    const editNotesTextarea = document.getElementById("editResolutionNotes");

    if (editReqIdInput) editReqIdInput.value = reqId;
    if (displayReqId) displayReqId.textContent = reqId;
    if (displayOrgService) displayOrgService.textContent = `${org} • ${service}`;
    if (editStatusSelect) editStatusSelect.value = currentStatus;
    if (editPrioritySelect) editPrioritySelect.value = priority;
    if (editAssignedToInput) editAssignedToInput.value = assigned;
    if (editDueDateInput) editDueDateInput.value = due;
    if (editNotesTextarea) editNotesTextarea.value = notes;

    updateStatusModal.classList.add("active");
    document.body.style.overflow = "hidden";
  }

  function closeUpdateStatusModal() {
    if (updateStatusModal) {
      updateStatusModal.classList.remove("active");
      document.body.style.overflow = "";
    }
  }

  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".btn-update-status");
    if (btn) {
      openUpdateStatusModal(btn);
    }
  });

  if (closeUpdateStatusModalBtn) {
    closeUpdateStatusModalBtn.addEventListener("click", closeUpdateStatusModal);
  }
  if (btnCancelUpdateStatus) {
    btnCancelUpdateStatus.addEventListener("click", closeUpdateStatusModal);
  }
  if (updateStatusModal) {
    updateStatusModal.addEventListener("click", (e) => {
      if (e.target === updateStatusModal) closeUpdateStatusModal();
    });
  }

  if (updateStatusForm) {
    updateStatusForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btnSave = document.getElementById("btnSaveStatus");
      if (btnSave) {
        btnSave.disabled = true;
        btnSave.innerHTML = `<span class="spinner spinner-dark" style="margin-right: 0.4rem;"></span> Updating...`;
      }

      const reqId = document.getElementById("editRequestId")?.value;
      if (!reqId) return;

      const formData = new FormData(updateStatusForm);
      const payload = {
        status: formData.get("status") || "Pending",
        priority: formData.get("priority") || "Medium",
        assigned_to: formData.get("assigned_to") || "",
        due_date: formData.get("due_date") || "",
        resolution_notes: formData.get("resolution_notes") || ""
      };

      try {
        const res = await fetch(`/api/requests/${encodeURIComponent(reqId)}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (res.status === 401) {
          window.location.href = "/login";
          throw new Error("Authentication required. Redirecting to login...");
        }

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail?.message || data.detail || "Failed to update request status.");
        }

        if (updateStatusFeedback) {
          updateStatusFeedback.style.display = "block";
          updateStatusFeedback.innerHTML = `
            <div style="background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; padding: 0.75rem 1rem; border-radius: 6px; font-size: 0.875rem;">
              <strong>Success:</strong> Request ${escapeHtml(reqId)} updated successfully.
            </div>
          `;
        }

        setTimeout(() => {
          closeUpdateStatusModal();
          window.location.reload();
        }, 1000);
      } catch (err) {
        if (updateStatusFeedback) {
          updateStatusFeedback.style.display = "block";
          updateStatusFeedback.innerHTML = `
            <div style="background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; padding: 0.75rem 1rem; border-radius: 6px; font-size: 0.875rem;">
              <strong>Error:</strong> ${escapeHtml(err.message)}
            </div>
          `;
        }
      } finally {
        if (btnSave) {
          btnSave.disabled = false;
          btnSave.innerHTML = `Update Request`;
        }
      }
    });
  }

  // Handle global escape key for all modals
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeSubmitRequestModal();
      closeUpdateStatusModal();
    }
  });

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
