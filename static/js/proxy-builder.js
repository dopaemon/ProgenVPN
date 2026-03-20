(function () {
  const form = document.getElementById("proxyForm");
  if (!form) {
    return;
  }

  const elements = {
    protocol: document.getElementById("protocol"),
    alertBox: document.getElementById("proxyAlert"),
    nodeList: document.getElementById("nodeList"),
    nodeTemplate: document.getElementById("proxyNodeTemplate"),
    resultTemplate: document.getElementById("proxyResultTemplate"),
    resultsPanel: document.getElementById("resultsPanel"),
    resultsMeta: document.getElementById("resultsMeta"),
    resultCountBadge: document.getElementById("resultCountBadge"),
    buildButton: document.getElementById("buildButton"),
    addNodeButton: document.getElementById("addNodeButton"),
    bulkUuidButton: document.getElementById("bulkUuidButton"),
    nodeCountStat: document.getElementById("nodeCountStat"),
    generatedCountStat: document.getElementById("generatedCountStat"),
    selectedProtocolStat: document.getElementById("selectedProtocolStat"),
  };

  const defaultNodes = JSON.parse(form.dataset.defaultNodes || "[]");
  let collapseSequence = 0;

  function nextCollapseId(prefix) {
    collapseSequence += 1;
    return prefix + "-" + collapseSequence;
  }

  function listNodeItems() {
    return Array.from(elements.nodeList.querySelectorAll(".node-item"));
  }

  function showAlert(message, type) {
    elements.alertBox.className = "alert alert-" + type;
    elements.alertBox.textContent = message;
    elements.alertBox.classList.remove("d-none");
  }

  function hideAlert() {
    elements.alertBox.classList.add("d-none");
  }

  function setLoadingState(isLoading) {
    elements.buildButton.disabled = isLoading;
    elements.buildButton.textContent = isLoading ? "Building..." : "Build Proxy";
  }

  function updateProtocolStat() {
    elements.selectedProtocolStat.textContent = elements.protocol.value.toUpperCase();
  }

  function updateNodeSummary() {
    elements.nodeCountStat.textContent = String(listNodeItems().length);
  }

  function updateGeneratedSummary(count) {
    elements.generatedCountStat.textContent = String(count);
    elements.resultCountBadge.textContent = count + " node" + (count === 1 ? "" : "s");
  }

  function setEmptyState() {
    elements.resultsMeta.textContent = "No results yet. Build at least one node to generate QR codes and import links.";
    elements.resultsPanel.innerHTML = [
      '<div class="proxy-empty-state text-center">',
      '  <div class="proxy-empty-title">Ready to build</div>',
      '  <div class="proxy-empty-copy text-gray-500">Results stay collapsed by default, while each card still shows basic node details.</div>',
      "</div>",
    ].join("");
    updateGeneratedSummary(0);
  }

  async function requestUuid() {
    const response = await fetch("/api/proxy/uuid");
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Unable to generate a UUID.");
    }
    return payload.uuid;
  }

  function refreshNodeCard(item, index) {
    const title = item.querySelector(".node-title");
    const subtitle = item.querySelector(".node-subtitle");
    const badge = item.querySelector(".node-badge");
    const remarkInput = item.querySelector(".node-remark");
    const portInput = item.querySelector(".node-port");
    const uuidInput = item.querySelector(".node-uuid");
    const expectedRemark = "Node " + (index + 1);

    title.textContent = expectedRemark;
    if (!remarkInput.value.trim() || /^Node \d+$/.test(remarkInput.value.trim())) {
      remarkInput.value = expectedRemark;
    }

    subtitle.textContent = "Port " + (portInput.value.trim() || "0") + " / UUID " + (uuidInput.value.trim() ? "ready" : "missing");
    badge.textContent = uuidInput.value.trim() ? "Ready" : "Needs UUID";
  }

  function refreshNodeCards() {
    listNodeItems().forEach(refreshNodeCard);
    updateNodeSummary();
  }

  function buildNodePayload(item) {
    return {
      remark: item.querySelector(".node-remark").value.trim(),
      port: item.querySelector(".node-port").value.trim(),
      uuid: item.querySelector(".node-uuid").value.trim(),
      alter_id: item.querySelector(".node-alter-id").value.trim(),
    };
  }

  function collectFormPayload() {
    return {
      protocol: document.getElementById("protocol").value,
      address: document.getElementById("address").value.trim(),
      network: document.getElementById("network").value,
      security: document.getElementById("security").value,
      host: document.getElementById("host").value.trim(),
      path: document.getElementById("path").value.trim(),
      sni: document.getElementById("sni").value.trim(),
      fingerprint: document.getElementById("fingerprint").value.trim(),
      alpn: document.getElementById("alpn").value.trim(),
      flow: document.getElementById("flow").value.trim(),
      header_type: document.getElementById("header_type").value.trim(),
      nodes: listNodeItems().map(buildNodePayload),
    };
  }

  function updateResultsMeta(payload) {
    elements.resultsMeta.textContent =
      "Built " +
      payload.node_count +
      " " +
      payload.protocol.toUpperCase() +
      " nodes for " +
      payload.address +
      ". Expand any card to view QR and copy actions.";
    updateGeneratedSummary(payload.node_count);
  }

  function createResultCard(item) {
    const fragment = elements.resultTemplate.content.cloneNode(true);
    const resultItem = fragment.querySelector(".result-item");
    const collapseId = nextCollapseId("result-collapse");
    const toggle = resultItem.querySelector(".result-toggle");
    const collapse = resultItem.querySelector(".result-collapse");

    toggle.setAttribute("href", "#" + collapseId);
    toggle.setAttribute("aria-controls", collapseId);
    toggle.setAttribute("aria-expanded", "false");
    collapse.id = collapseId;

    resultItem.querySelector(".result-remark").textContent = item.remark;
    resultItem.querySelector(".result-port-text").textContent = "Port " + item.port;
    resultItem.querySelector(".result-status").textContent = "Ready";
    resultItem.querySelector(".result-qr").src = item.qr_code_data_uri;
    resultItem.querySelector(".result-qr").alt = "QR " + item.remark;
    resultItem.querySelector(".result-uuid").value = item.uuid;
    resultItem.querySelector(".result-link").value = item.share_link;
    resultItem.querySelector(".result-payload").value = item.payload_json;

    return fragment;
  }

  function renderResults(payload) {
    if (!payload.results || !payload.results.length) {
      setEmptyState();
      return;
    }

    const fragment = document.createDocumentFragment();
    payload.results.forEach(function (item) {
      fragment.appendChild(createResultCard(item));
    });

    elements.resultsPanel.innerHTML = "";
    elements.resultsPanel.appendChild(fragment);
    updateResultsMeta(payload);
  }

  async function copyText(button, text, successLabel) {
    const originalLabel = button.textContent;
    try {
      await navigator.clipboard.writeText(text);
      button.textContent = successLabel;
      setTimeout(function () {
        button.textContent = originalLabel;
      }, 1200);
    } catch (error) {
      showAlert("Unable to copy to the clipboard.", "warning");
    }
  }

  async function fillNodeUuid(input) {
    input.value = "Generating...";
    try {
      input.value = await requestUuid();
    } catch (error) {
      input.value = "";
      showAlert(error.message, "danger");
    }
  }

  function bindNodeEvents(item) {
    item.querySelector(".remove-node").addEventListener("click", function () {
      if (listNodeItems().length === 1) {
        showAlert("At least one node is required.", "warning");
        return;
      }
      item.remove();
      refreshNodeCards();
    });

    item.querySelector(".generate-uuid").addEventListener("click", async function () {
      hideAlert();
      await fillNodeUuid(item.querySelector(".node-uuid"));
      refreshNodeCards();
    });

    item.querySelector(".node-remark").addEventListener("input", refreshNodeCards);
    item.querySelector(".node-port").addEventListener("input", refreshNodeCards);
    item.querySelector(".node-uuid").addEventListener("input", refreshNodeCards);
  }

  function addNode(node) {
    const fragment = elements.nodeTemplate.content.cloneNode(true);
    const item = fragment.querySelector(".node-item");
    const collapseId = nextCollapseId("node-collapse");
    const toggle = item.querySelector(".node-toggle");
    const collapse = item.querySelector(".node-collapse");

    toggle.setAttribute("href", "#" + collapseId);
    toggle.setAttribute("aria-controls", collapseId);
    toggle.setAttribute("aria-expanded", "false");
    collapse.id = collapseId;

    item.querySelector(".node-remark").value = node.remark || "";
    item.querySelector(".node-port").value = node.port || 443;
    item.querySelector(".node-uuid").value = node.uuid || "";
    item.querySelector(".node-alter-id").value = node.alter_id != null ? node.alter_id : 0;

    bindNodeEvents(item);
    elements.nodeList.appendChild(fragment);
    refreshNodeCards();
  }

  async function buildProxy(event) {
    event.preventDefault();
    hideAlert();
    setLoadingState(true);

    try {
      const response = await fetch("/api/proxy/build", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(collectFormPayload()),
      });
      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.error || "Unable to build the proxy set.");
      }

      renderResults(payload);
      showAlert("Built " + payload.node_count + " " + payload.protocol.toUpperCase() + " nodes.", "success");
    } catch (error) {
      showAlert(error.message, "danger");
    } finally {
      setLoadingState(false);
    }
  }

  async function fillEmptyUuids() {
    const emptyInputs = listNodeItems()
      .map(function (item) {
        return item.querySelector(".node-uuid");
      })
      .filter(function (input) {
        return !input.value.trim();
      });

    if (!emptyInputs.length) {
      showAlert("Every node already has a UUID.", "info");
      return;
    }

    hideAlert();
    for (const input of emptyInputs) {
      await fillNodeUuid(input);
      if (!input.value.trim()) {
        break;
      }
    }
    refreshNodeCards();
  }

  function handleResultsClick(event) {
    const copyLinkButton = event.target.closest(".copy-link-button");
    if (copyLinkButton) {
      const resultItem = copyLinkButton.closest(".result-item");
      copyText(copyLinkButton, resultItem.querySelector(".result-link").value, "Copied");
      return;
    }

    const copyPayloadButton = event.target.closest(".copy-payload-button");
    if (copyPayloadButton) {
      const resultItem = copyPayloadButton.closest(".result-item");
      copyText(copyPayloadButton, resultItem.querySelector(".result-payload").value, "Copied");
    }
  }

  elements.addNodeButton.addEventListener("click", function () {
    addNode({ port: 443, alter_id: 0 });
  });
  elements.bulkUuidButton.addEventListener("click", fillEmptyUuids);
  elements.protocol.addEventListener("change", updateProtocolStat);
  elements.resultsPanel.addEventListener("click", handleResultsClick);
  form.addEventListener("submit", buildProxy);

  setEmptyState();
  updateProtocolStat();
  defaultNodes.forEach(addNode);
}());
