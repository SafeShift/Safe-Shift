/**
 * SafeShift Demo Dashboard — SSE event handler
 * Owner: Josh
 *
 * Connects to GET /stream and updates the UI as events arrive.
 *
 * Event types and handlers:
 *   "frame"        → updateMetrics(data)
 *   "vlm"          → updatePerceptionPanel(data)
 *   "decision"     → updateSafetyPanel(data)
 *   "companion"    → appendCompanionMessage(data)
 *   "intervention" → appendInterventionLog(data)
 */

const stream = new EventSource("/stream");

stream.addEventListener("message", (e) => {
  const event = JSON.parse(e.data);
  switch (event.type) {
    case "frame":        updateMetrics(event.data);          break;
    case "vlm":          updatePerceptionPanel(event.data);  break;
    case "decision":     updateSafetyPanel(event.data);      break;
    case "companion":    appendCompanionMessage(event.data); break;
    case "intervention": appendInterventionLog(event.data);  break;
  }
});

stream.onerror = () => {
  document.getElementById("shift-status").textContent = "Connection lost — retrying...";
};

// --- Panel updaters (implement below) ---

function updateMetrics(data) {
  // data: FrameAnalysis fields
  // TODO: update #metric-eye-openness, #metric-blink-rate, #metric-gaze
  // TODO: update fatigue gauge
  throw new Error("Not implemented");
}

function updatePerceptionPanel(data) {
  // data: VLMFrameAssessment fields
  // TODO: update #vlm-description, #vlm-flags, #vlm-confidence
  // TODO: update #severity-badge
  throw new Error("Not implemented");
}

function updateSafetyPanel(data) {
  // data: InterventionDecision fields
  // TODO: append ReAct step to #react-trace
  // TODO: update #intervention-decision with severity + reason
  throw new Error("Not implemented");
}

function appendCompanionMessage(data) {
  // data: CompanionMessage fields
  // TODO: append chat bubble to #companion-messages
  // TODO: auto-scroll
  throw new Error("Not implemented");
}

function appendInterventionLog(data) {
  // data: InterventionRecord fields
  // TODO: prepend <li> to #log-list with timestamp, type, severity, summary
  throw new Error("Not implemented");
}
