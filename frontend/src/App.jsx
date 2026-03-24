import { useState } from "react";

const AGENT_FLOW = [
  {
    id: "input",
    name: "AI Generated Response",
    description: "Input",
    icon: "⟲",
    section: "INPUT",
  },
  {
    id: "gatekeeper",
    name: "Gatekeeper ML Model",
    description: "Screening Agent",
    icon: "◉",
    section: "SCREENING",
  },
  {
    id: "router",
    name: "Smart Routing",
    description: "Routing Agent",
    icon: "⊗",
    section: "ROUTING",
  },
  {
    id: "vectorkb",
    name: "Multi Agent RAG Retrieval",
    description: "Retrieval Agent",
    icon: "⊞",
    section: "RETRIEVAL",
  },
  {
    id: "rag",
    name: "Draft Correction",
    description: "Correction Agent",
    icon: "⊘",
    section: "CORRECTION",
  },
  {
    id: "consensus",
    name: "Consensus Validation",
    description: "Arbitration Agent",
    icon: "◎",
    section: "VALIDATION",
  },
  {
    id: "scoring",
    name: "Explainability & Confidence",
    description: "Scoring Agent",
    icon: "⊡",
    section: "SCORING",
  },
  {
    id: "complete",
    name: "Final Output",
    description: "System Output",
    icon: "◈",
    section: "OUTPUT",
  },
];

const MODEL_METRICS = {
  hallucination: {
    name: "Hallucination Detection",
    metrics: {
      "No Hallucination": {
        precision: 0.93,
        recall: 0.88,
        f1: 0.9,
        support: 16,
      },
      Hallucination: { precision: 0.88, recall: 0.93, f1: 0.9, support: 15 },
    },
    accuracy: 0.9,
    confusionMatrix: [
      [14, 2],
      [1, 14],
    ],
    supportVectors: 119,
    labels: ["No Hall", "Hall"],
  },
  bias: {
    name: "Bias Detection",
    metrics: {
      "No Bias": { precision: 0.86, recall: 1.0, f1: 0.92, support: 18 },
      Bias: { precision: 1.0, recall: 0.77, f1: 0.87, support: 13 },
    },
    accuracy: 0.9,
    confusionMatrix: [
      [18, 0],
      [3, 10],
    ],
    supportVectors: 114,
    labels: ["No Bias", "Bias"],
  },
};

const styles = `
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Space+Grotesk:wght@300;400;500;600;700&family=Outfit:wght@200;300;400;500;600;700;800&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f8f9fa;
  --bg-tertiary: #f0f1f3;
  --bg-elevated: #e8eaed;
  --border-subtle: #d0d5dd;
  --border-medium: #98a2b3;
  --border-strong: #667085;
  --text-primary: #101828;
  --text-secondary: #344054;
  --text-muted: #667085;
  --accent-black: #101828;
  --accent-green: #12B76A;
  --accent-red: #F04438;
  --accent-yellow: #F79009;
  --accent-blue: #0BA5EC;
  --shadow-sm: 0 1px 2px rgba(16,24,40,0.05);
  --shadow-md: 0 4px 8px -2px rgba(16,24,40,0.1), 0 2px 4px -2px rgba(16,24,40,0.06);
  --shadow-lg: 0 12px 16px -4px rgba(16,24,40,0.08), 0 4px 6px -2px rgba(16,24,40,0.03);
}

body { font-family: 'Outfit', sans-serif; background: var(--bg-primary); color: var(--text-primary); min-height: 100vh; }

.app {
  min-height: 100vh;
  background: radial-gradient(ellipse at 20% 0%, rgba(0,0,0,0.02) 0%, transparent 50%), radial-gradient(ellipse at 80% 100%, rgba(0,0,0,0.02) 0%, transparent 50%), var(--bg-primary);
}

.app::before {
  content: ''; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background-image: linear-gradient(rgba(0,0,0,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,0,0,0.03) 1px, transparent 1px);
  background-size: 50px 50px; pointer-events: none; z-index: 0;
}

.container { max-width: 1600px; margin: 0 auto; padding: 40px 60px; position: relative; z-index: 1; }

.header { text-align: center; margin-bottom: 60px; position: relative; }
.header::after { content: ''; position: absolute; bottom: -30px; left: 50%; transform: translateX(-50%); width: 200px; height: 2px; background: linear-gradient(90deg, transparent, var(--border-medium), transparent); }

.title-box h1 {
  font-family: 'Space Grotesk', sans-serif; font-size: 3.5rem; font-weight: 700; letter-spacing: -0.02em;
  background: linear-gradient(135deg, #101828 0%, #344054 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 12px;
}

.subtitle { font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: var(--text-muted); letter-spacing: 0.15em; text-transform: uppercase; }

.input-form { background: var(--bg-secondary); border: 2px solid var(--border-subtle); border-radius: 16px; padding: 40px; margin-bottom: 60px; position: relative; box-shadow: var(--shadow-md); }
.input-form::before { content: 'INPUT'; position: absolute; top: 16px; left: 20px; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-muted); letter-spacing: 0.2em; }

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 20px; }
.form-group { display: flex; flex-direction: column; gap: 10px; }
.form-group label { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--text-secondary); letter-spacing: 0.1em; text-transform: uppercase; font-weight: 600; }
.form-group textarea { background: var(--bg-primary); border: 2px solid var(--border-subtle); border-radius: 8px; padding: 16px; font-family: 'Outfit', sans-serif; font-size: 0.95rem; color: var(--text-primary); resize: vertical; min-height: 120px; transition: all 0.3s ease; }
.form-group textarea:focus { outline: none; border-color: var(--accent-black); box-shadow: 0 0 0 4px rgba(16,24,40,0.1); }
.form-group textarea::placeholder { color: var(--text-muted); }

.submit-btn { margin-top: 30px; width: 100%; padding: 18px 40px; background: var(--accent-black); color: var(--bg-primary); border: none; border-radius: 8px; font-family: 'Space Grotesk', sans-serif; font-size: 0.9rem; font-weight: 600; letter-spacing: 0.15em; text-transform: uppercase; cursor: pointer; transition: all 0.3s ease; box-shadow: var(--shadow-md); }
.submit-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: var(--shadow-lg); }
.submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.submit-btn.processing { background: var(--bg-primary); border: 2px solid var(--accent-black); color: var(--accent-black); }

.error-box { background: rgba(240,68,56,0.08); border: 2px solid var(--accent-red); border-radius: 12px; padding: 20px; margin-bottom: 40px; }
.error-title { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--accent-red); letter-spacing: 0.2em; margin-bottom: 8px; font-weight: 700; }
.error-message { color: var(--text-secondary); font-size: 0.9rem; }

.pipeline-section { margin-top: 60px; }
.section-header { display: flex; align-items: center; gap: 16px; margin-bottom: 40px; }
.section-title { font-family: 'Space Grotesk', sans-serif; font-size: 1.5rem; font-weight: 700; color: var(--text-primary); }
.section-line { flex: 1; height: 2px; background: linear-gradient(90deg, var(--border-medium), transparent); }

.visual-flow { margin-top: 40px; padding: 40px; background: var(--bg-secondary); border: 2px solid var(--border-subtle); border-radius: 20px; overflow-x: auto; box-shadow: var(--shadow-md); }
.flow-diagram { display: flex; flex-direction: column; gap: 30px; min-width: 1200px; }
.flow-row { display: flex; align-items: center; gap: 20px; }

.flow-box { display: flex; flex-direction: column; align-items: center; padding: 20px 28px; border-radius: 12px; background: var(--bg-primary); border: 2px solid var(--border-medium); min-width: 140px; transition: all 0.3s ease; box-shadow: var(--shadow-sm); }
.flow-box.input { background: #E0F2FE; border-color: var(--accent-blue); border-radius: 50px; }
.flow-box.screening { background: #FEF3C7; border-color: #F59E0B; }
.flow-box.routing { background: #FCE7F3; border-color: #EC4899; }
.flow-box.route-option { background: var(--bg-primary); border-color: var(--border-strong); min-width: 120px; padding: 14px 20px; opacity: 0.5; }
.flow-box.route-option.bias { background: #FEE2E2; border-color: #EF4444; }
.flow-box.route-option.factual { background: #DBEAFE; border-color: #3B82F6; }
.flow-box.route-option.logical { background: #E0E7FF; border-color: #6366F1; }
.flow-box.route-option.temporal { background: #FEF3C7; border-color: #F59E0B; }
.flow-box.route-option.route-active { opacity: 1; box-shadow: 0 0 0 4px rgba(16,24,40,0.15), var(--shadow-lg); transform: scale(1.08); }
.flow-box.retrieval { background: #DBEAFE; border-color: #3B82F6; }
.flow-box.correction { background: #D1FAE5; border-color: #10B981; }
.flow-box.validation { background: #D1FAE5; border-color: #10B981; }
.flow-box.scoring { background: #CCFBF1; border-color: #14B8A6; }
.flow-box.output-verified { background: var(--accent-green); border-color: var(--accent-green); border-radius: 50px; }
.flow-box.output-review { background: #FEF3C7; border-color: var(--accent-yellow); border-radius: 50px; }
.flow-box.active { box-shadow: 0 0 0 4px rgba(16,24,40,0.15), var(--shadow-lg); transform: scale(1.05); }
.flow-box.complete { border-color: var(--accent-green); box-shadow: 0 0 0 3px rgba(18,183,106,0.2); }
.flow-box.pending { opacity: 0.4; }
.flow-box-icon { font-size: 1.2rem; margin-bottom: 8px; color: var(--text-primary); }
.flow-box-name { font-family: 'Space Grotesk', sans-serif; font-size: 0.8rem; font-weight: 600; color: var(--text-primary); text-align: center; }
.flow-box.output-verified .flow-box-name { color: var(--bg-primary); }

.flow-arrow { font-size: 1.8rem; color: var(--border-medium); transition: color 0.3s ease; font-weight: bold; }
.flow-arrow.active { color: var(--accent-green); }

.section-container { border: 2px dashed var(--border-subtle); border-radius: 16px; padding: 24px; position: relative; display: flex; align-items: center; gap: 16px; background: rgba(255,255,255,0.5); }
.section-container.routing-section { border-color: rgba(236,72,153,0.4); background: rgba(252,231,243,0.3); }
.section-container.retrieval-section { border-color: rgba(59,130,246,0.4); background: rgba(219,234,254,0.3); }
.section-container.correction-section { border-color: rgba(16,185,129,0.4); background: rgba(209,250,229,0.3); }
.section-container.scoring-section { border-color: rgba(20,184,166,0.4); background: rgba(204,251,241,0.3); }
.section-tag { position: absolute; top: -12px; left: 20px; background: var(--bg-primary); padding: 4px 12px; font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: var(--text-muted); letter-spacing: 0.15em; text-transform: uppercase; font-weight: 600; border-radius: 4px; }

.routes-column { display: flex; flex-direction: column; gap: 8px; }
.validators-row { display: flex; flex-direction: column; gap: 12px; }
.outputs-column { display: flex; flex-direction: column; gap: 16px; align-items: center; }
.confidence-label { font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; }

.agent-output-card { background: var(--bg-secondary); border: 2px solid var(--border-subtle); border-radius: 16px; padding: 24px; margin-top: 30px; box-shadow: var(--shadow-md); }
.agent-output-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; }
.output-item { display: flex; flex-direction: column; gap: 6px; padding: 16px; background: var(--bg-primary); border-radius: 10px; border: 1px solid var(--border-subtle); }
.output-label { font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; }
.output-value { font-family: 'Space Grotesk', sans-serif; font-size: 1.1rem; font-weight: 700; color: var(--text-primary); }
.output-value.positive { color: var(--accent-green); }
.output-value.negative { color: var(--accent-red); }
.output-value.warning { color: var(--accent-yellow); }

.final-comparison { margin-top: 60px; }
.comparison-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin-top: 30px; }
.comparison-card { background: var(--bg-secondary); border: 2px solid var(--border-subtle); border-radius: 16px; overflow: hidden; box-shadow: var(--shadow-md); }
.comparison-card.highlight { border-color: var(--accent-green); box-shadow: 0 0 0 4px rgba(18,183,106,0.15), var(--shadow-lg); }
.card-header { padding: 16px 20px; background: var(--bg-tertiary); border-bottom: 2px solid var(--border-subtle); }
.card-title { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--text-secondary); letter-spacing: 0.2em; text-transform: uppercase; font-weight: 700; }
.card-content { padding: 20px; font-size: 0.9rem; line-height: 1.6; color: var(--text-secondary); max-height: 200px; overflow-y: auto; }
.card-content.corrected { color: var(--accent-green); font-weight: 500; }

.final-metrics { display: flex; justify-content: center; gap: 60px; margin-top: 40px; padding: 30px; background: var(--bg-secondary); border: 2px solid var(--border-subtle); border-radius: 16px; box-shadow: var(--shadow-md); }
.metric-item { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.metric-label { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--text-muted); letter-spacing: 0.15em; text-transform: uppercase; font-weight: 600; }
.metric-value { font-family: 'Space Grotesk', sans-serif; font-size: 2.5rem; font-weight: 700; color: var(--text-primary); }
.metric-value.verified { color: var(--accent-green); }
.metric-value.needs_review { color: var(--accent-yellow); }

.retrieved-docs { margin-top: 40px; }
.docs-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 24px; }
.doc-card { background: var(--bg-secondary); border: 2px solid var(--border-subtle); border-radius: 12px; overflow: hidden; box-shadow: var(--shadow-sm); }
.doc-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: var(--bg-tertiary); border-bottom: 2px solid var(--border-subtle); }
.doc-number { font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; font-weight: 700; color: var(--text-primary); }
.doc-similarity { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--accent-green); font-weight: 600; }
.doc-content { padding: 16px; font-size: 0.85rem; line-height: 1.5; }
.doc-question, .doc-answer { margin-bottom: 8px; }
.doc-question strong, .doc-answer strong { color: var(--text-muted); }

.evaluation-section { margin-top: 80px; }
.eval-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 30px; }
.eval-card { background: var(--bg-secondary); border: 2px solid var(--border-subtle); border-radius: 20px; overflow: hidden; box-shadow: var(--shadow-md); }
.eval-header { padding: 24px; background: var(--bg-tertiary); border-bottom: 2px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center; }
.eval-title { font-family: 'Space Grotesk', sans-serif; font-size: 1.3rem; font-weight: 700; color: var(--text-primary); }
.eval-accuracy { display: flex; flex-direction: column; align-items: flex-end; }
.accuracy-label { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-muted); letter-spacing: 0.1em; font-weight: 600; }
.accuracy-value { font-family: 'Space Grotesk', sans-serif; font-size: 2.8rem; font-weight: 700; color: var(--accent-green); }
.eval-body { padding: 24px; }

.metrics-table { width: 100%; border-collapse: collapse; margin-bottom: 24px; }
.metrics-table th, .metrics-table td { padding: 14px 16px; text-align: left; border-bottom: 2px solid var(--border-subtle); }
.metrics-table th { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-muted); letter-spacing: 0.1em; text-transform: uppercase; background: var(--bg-tertiary); font-weight: 700; }
.metrics-table td { font-family: 'Space Grotesk', sans-serif; font-size: 0.95rem; color: var(--text-secondary); }
.metrics-table td:first-child { font-weight: 600; color: var(--text-primary); }
.metrics-table tr:last-child td { border-bottom: none; }
.metric-highlight { color: var(--accent-green) !important; font-weight: 700 !important; }

.confusion-section { margin-top: 24px; }
.confusion-title { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--text-muted); letter-spacing: 0.15em; text-transform: uppercase; margin-bottom: 16px; font-weight: 700; }
.confusion-matrix { display: inline-block; background: var(--bg-tertiary); border-radius: 12px; padding: 20px; border: 2px solid var(--border-subtle); }
.matrix-label-row { display: flex; justify-content: center; gap: 40px; margin-bottom: 12px; padding-left: 80px; }
.matrix-label { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; width: 60px; text-align: center; font-weight: 600; }
.matrix-row { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.matrix-row-label { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; width: 80px; text-align: right; font-weight: 600; }
.matrix-cells { display: flex; gap: 8px; }
.matrix-cell { width: 65px; height: 65px; display: flex; align-items: center; justify-content: center; font-family: 'Space Grotesk', sans-serif; font-size: 1.4rem; font-weight: 700; border-radius: 10px; }
.matrix-cell.diagonal { background: var(--accent-green); color: var(--bg-primary); }
.matrix-cell.off-diagonal { background: var(--bg-primary); color: var(--text-secondary); border: 2px solid var(--border-subtle); }
.matrix-cell.error { background: rgba(240,68,56,0.15); color: var(--accent-red); border: 2px solid var(--accent-red); }

.model-stats { margin-top: 24px; padding: 18px; background: var(--bg-tertiary); border-radius: 12px; border: 2px solid var(--border-subtle); }
.stat-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; }
.stat-label { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--text-muted); letter-spacing: 0.05em; font-weight: 600; }
.stat-value { font-family: 'Space Grotesk', sans-serif; font-size: 1.2rem; font-weight: 700; color: var(--text-primary); }

.dataset-info { background: var(--bg-secondary); border: 2px solid var(--border-subtle); border-radius: 16px; padding: 28px; margin-bottom: 30px; box-shadow: var(--shadow-md); }
.dataset-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; }
.dataset-item { display: flex; flex-direction: column; gap: 6px; padding: 16px; background: var(--bg-primary); border-radius: 10px; border: 1px solid var(--border-subtle); }
.dataset-label { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: var(--text-muted); letter-spacing: 0.1em; text-transform: uppercase; font-weight: 600; }
.dataset-value { font-family: 'Space Grotesk', sans-serif; font-size: 1.8rem; font-weight: 700; color: var(--text-primary); }
.dataset-value span { font-size: 0.9rem; color: var(--text-muted); font-weight: 500; }

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--bg-tertiary); }
::-webkit-scrollbar-thumb { background: var(--border-medium); border-radius: 4px; }

@media (max-width: 1200px) {
  .container { padding: 30px; }
  .form-row, .comparison-grid, .eval-grid { grid-template-columns: 1fr; }
  .dataset-grid { grid-template-columns: repeat(2, 1fr); }
}
`;

function App() {
  const [userMessage, setUserMessage] = useState("");
  const [aiResponse, setAiResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentStep, setCurrentStep] = useState(-1);
  const [agentResults, setAgentResults] = useState({});
  const [finalResult, setFinalResult] = useState(null);
  const [pipelineActive, setPipelineActive] = useState(false);
  const [activeRoute, setActiveRoute] = useState(null);
  const [pipelineComplete, setPipelineComplete] = useState(false);

  const resetPipeline = () => {
    setCurrentStep(-1);
    setAgentResults({});
    setFinalResult(null);
    setPipelineActive(false);
    setPipelineComplete(false);
    setError(null);
    setActiveRoute(null);
  };

  // Normalize category to match route options
  const normalizeCategory = (category) => {
    if (!category) return null;
    const cat = category.toLowerCase();
    // Handle variations like "factual_error", "factual", "factual error"
    if (cat.includes("factual")) return "factual";
    if (cat.includes("bias")) return "bias";
    if (cat.includes("logical")) return "logical";
    if (cat.includes("temporal")) return "temporal";
    return cat;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    resetPipeline();
    setPipelineActive(true);
    try {
      const response = await fetch(
        "http://localhost:5174/api/pipeline/stream",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_message: userMessage,
            ai_response: aiResponse,
          }),
        },
      );
      if (!response.ok)
        throw new Error(`HTTP error! status: ${response.status}`);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let collectedRoute = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const lines = decoder.decode(value).split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.step === "error") {
                setError(data.message);
                setPipelineActive(false);
                break;
              }
              const stepIndex = AGENT_FLOW.findIndex((a) => a.id === data.step);
              if (stepIndex !== -1 && data.status === "processing")
                setCurrentStep(stepIndex);
              if (data.status === "complete" && data.data) {
                setAgentResults((prev) => ({
                  ...prev,
                  [data.step]: data.data,
                }));
                setCurrentStep(stepIndex);
                // Collect route but don't display yet
                if (data.step === "router" && data.data.category) {
                  collectedRoute = normalizeCategory(data.data.category);
                }
              }
              if (data.step === "complete") {
                setFinalResult(data.data || data);
                setPipelineActive(false);
                setPipelineComplete(true);
                setCurrentStep(AGENT_FLOW.length - 1);
                // Now set the active route for display
                setActiveRoute(collectedRoute);
              }
            } catch (e) {
              console.error("Parse error:", e);
            }
          }
        }
      }
    } catch (err) {
      setError(err.message);
      setPipelineActive(false);
    } finally {
      setLoading(false);
    }
  };

  const getStepStatus = (stepId) => {
    const idx = AGENT_FLOW.findIndex((a) => a.id === stepId);
    if (pipelineComplete) {
      return "complete";
    }
    return idx < currentStep
      ? "complete"
      : idx === currentStep
        ? "active"
        : "pending";
  };

  // Check if a route should be highlighted
  const isRouteActive = (routeName) => {
    if (!pipelineComplete || !activeRoute) return false;
    return activeRoute === routeName;
  };

  return (
    <>
      <style>{styles}</style>
      <div className="app">
        <div className="container">
          <header className="header">
            <div className="title-box">
              <h1>MULTI-AGENT RAG PIPELINE</h1>
              <div className="subtitle">
                Audit-Ready Hallucination & Bias Detection System
              </div>
            </div>
          </header>

          <form onSubmit={handleSubmit} className="input-form">
            <div className="form-row">
              <div className="form-group">
                <label>User Prompt / Question</label>
                <textarea
                  value={userMessage}
                  onChange={(e) => setUserMessage(e.target.value)}
                  placeholder="Enter the user's question or prompt..."
                  rows="4"
                  required
                />
              </div>
              <div className="form-group">
                <label>AI Response to Evaluate</label>
                <textarea
                  value={aiResponse}
                  onChange={(e) => setAiResponse(e.target.value)}
                  placeholder="Enter the AI's response to be evaluated..."
                  rows="4"
                  required
                />
              </div>
            </div>
            <button
              type="submit"
              className={`submit-btn ${loading ? "processing" : ""}`}
              disabled={loading}
            >
              {loading ? "◉ PROCESSING PIPELINE..." : "ANALYZE RESPONSE"}
            </button>
          </form>

          {error && (
            <div className="error-box">
              <div className="error-title">ERROR</div>
              <div className="error-message">{error}</div>
            </div>
          )}

          {(pipelineActive || currentStep >= 0) && (
            <div className="pipeline-section">
              <div className="section-header">
                <div className="section-title">Pipeline Execution Flow</div>
                <div className="section-line"></div>
              </div>
              <div className="visual-flow">
                <div className="flow-diagram">
                  <div className="flow-row">
                    <div className={`flow-box input ${getStepStatus("input")}`}>
                      <div className="flow-box-icon">⟲</div>
                      <div className="flow-box-name">
                        AI Generated
                        <br />
                        Response
                      </div>
                    </div>
                    <div
                      className={`flow-arrow ${getStepStatus("gatekeeper") !== "pending" ? "active" : ""}`}
                    >
                      →
                    </div>
                    <div
                      className="section-container"
                      style={{
                        borderColor: "rgba(245,158,11,0.5)",
                        background: "rgba(254,243,199,0.3)",
                      }}
                    >
                      <div className="section-tag">SCREENING</div>
                      <div
                        className={`flow-box screening ${getStepStatus("gatekeeper")}`}
                      >
                        <div className="flow-box-icon">◉</div>
                        <div className="flow-box-name">
                          Gatekeeper ML
                          <br />
                          Model
                        </div>
                      </div>
                    </div>
                    <div
                      className={`flow-arrow ${getStepStatus("router") !== "pending" ? "active" : ""}`}
                    >
                      →
                    </div>
                    <div className="section-container routing-section">
                      <div className="section-tag">ROUTING</div>
                      <div
                        className={`flow-box routing ${getStepStatus("router")}`}
                      >
                        <div className="flow-box-icon">⊗</div>
                        <div className="flow-box-name">
                          Smart
                          <br />
                          Routing
                        </div>
                      </div>
                      <div className="routes-column">
                        <div
                          className={`flow-box route-option factual ${isRouteActive("factual") ? "route-active" : ""}`}
                        >
                          <div className="flow-box-name">Factual Route</div>
                        </div>
                        <div
                          className={`flow-box route-option bias ${isRouteActive("bias") ? "route-active" : ""}`}
                        >
                          <div className="flow-box-name">Bias Route</div>
                        </div>
                        <div
                          className={`flow-box route-option logical ${isRouteActive("logical") ? "route-active" : ""}`}
                        >
                          <div className="flow-box-name">Logical Route</div>
                        </div>
                        <div
                          className={`flow-box route-option temporal ${isRouteActive("temporal") ? "route-active" : ""}`}
                        >
                          <div className="flow-box-name">Temporal Route</div>
                        </div>
                      </div>
                    </div>
                    <div
                      className={`flow-arrow ${getStepStatus("vectorkb") !== "pending" ? "active" : ""}`}
                    >
                      →
                    </div>
                    <div className="section-container retrieval-section">
                      <div className="section-tag">RETRIEVAL</div>
                      <div
                        className={`flow-box retrieval ${getStepStatus("vectorkb")}`}
                      >
                        <div className="flow-box-icon">⊞</div>
                        <div className="flow-box-name">
                          Multi Agent RAG
                          <br />
                          Retrieval
                        </div>
                      </div>
                      <div
                        className={`flow-arrow ${getStepStatus("vectorkb") !== "pending" ? "active" : ""}`}
                      >
                        →
                      </div>
                      <div
                        className={`flow-box retrieval ${getStepStatus("vectorkb")}`}
                      >
                        <div className="flow-box-icon">⊟</div>
                        <div className="flow-box-name">
                          Specialized
                          <br />
                          Knowledge Bases
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="flow-row">
                    <div className="section-container correction-section">
                      <div className="section-tag">
                        CORRECTION AND VALIDATION
                      </div>
                      <div
                        className={`flow-box correction ${getStepStatus("rag")}`}
                      >
                        <div className="flow-box-icon">⊘</div>
                        <div className="flow-box-name">
                          Draft
                          <br />
                          Correction
                        </div>
                      </div>
                      <div
                        className={`flow-arrow ${getStepStatus("consensus") !== "pending" ? "active" : ""}`}
                      >
                        →
                      </div>
                      <div
                        className={`flow-box validation ${getStepStatus("consensus")}`}
                      >
                        <div className="flow-box-icon">◎</div>
                        <div className="flow-box-name">
                          Consensus
                          <br />
                          Validation
                        </div>
                      </div>
                      <div className="validators-row">
                        <div
                          className={`flow-box validation ${getStepStatus("validator_openai")}`}
                        >
                          <div className="flow-box-icon">⊕</div>
                          <div className="flow-box-name">
                            OpenAI
                            <br />
                            Validation
                          </div>
                        </div>
                        <div
                          className={`flow-box validation ${getStepStatus("validator_gemini")}`}
                        >
                          <div className="flow-box-icon">⊕</div>
                          <div className="flow-box-name">
                            Gemini
                            <br />
                            Validation
                          </div>
                        </div>
                      </div>
                    </div>
                    <div
                      className={`flow-arrow ${getStepStatus("scoring") !== "pending" ? "active" : ""}`}
                    >
                      →
                    </div>
                    <div className="section-container scoring-section">
                      <div className="section-tag">SCORING AND OUTPUT</div>
                      <div
                        className={`flow-box scoring ${getStepStatus("scoring")}`}
                      >
                        <div className="flow-box-icon">⊡</div>
                        <div className="flow-box-name">
                          Explainability
                          <br />
                          and Confidence
                          <br />
                          Scoring
                        </div>
                      </div>
                      <div className="outputs-column">
                        <div>
                          <div className="confidence-label">
                            High Confidence
                          </div>
                          <div
                            className={`flow-box output-verified ${pipelineComplete && (finalResult?.final_status === "verified" || finalResult?.status === "verified") ? "active" : "pending"}`}
                          >
                            <div className="flow-box-icon">✓</div>
                            <div className="flow-box-name">Verified Output</div>
                          </div>
                        </div>
                        <div>
                          <div className="confidence-label">Low Confidence</div>
                          <div
                            className={`flow-box output-review ${pipelineComplete && (finalResult?.final_status === "needs_review" || finalResult?.status === "needs_review") ? "active" : "pending"}`}
                          >
                            <div className="flow-box-icon">⊙</div>
                            <div className="flow-box-name">
                              Needs Review
                              <br />
                              Output
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {Object.keys(agentResults).length > 0 && (
                <div className="agent-output-card">
                  <div className="section-header">
                    <div className="section-title">Agent Outputs</div>
                    <div className="section-line"></div>
                  </div>
                  <div
                    className="agent-output-grid"
                    style={{ marginTop: "20px" }}
                  >
                    {agentResults.gatekeeper && (
                      <>
                        <div className="output-item">
                          <span className="output-label">Hallucination</span>
                          <span
                            className={`output-value ${agentResults.gatekeeper.hallucination_detected ? "negative" : "positive"}`}
                          >
                            {agentResults.gatekeeper.hallucination_detected
                              ? "DETECTED"
                              : "CLEAN"}
                          </span>
                        </div>
                        <div className="output-item">
                          <span className="output-label">Confidence</span>
                          <span className="output-value">
                            {(
                              agentResults.gatekeeper.hallucination_confidence *
                              100
                            ).toFixed(1)}
                            %
                          </span>
                        </div>
                        <div className="output-item">
                          <span className="output-label">Bias</span>
                          <span
                            className={`output-value ${agentResults.gatekeeper.bias_detected ? "warning" : "positive"}`}
                          >
                            {agentResults.gatekeeper.bias_detected
                              ? "DETECTED"
                              : "CLEAN"}
                          </span>
                        </div>
                      </>
                    )}
                    {agentResults.router && (
                      <div className="output-item">
                        <span className="output-label">Route Category</span>
                        <span className="output-value">
                          {agentResults.router.category?.toUpperCase()}
                        </span>
                      </div>
                    )}
                    {agentResults.vectorkb && (
                      <div className="output-item">
                        <span className="output-label">Retrieved Docs</span>
                        <span className="output-value">
                          {agentResults.vectorkb.retrieved_count}
                        </span>
                      </div>
                    )}
                    {agentResults.validator_openai && (
                      <div className="output-item">
                        <span className="output-label">OpenAI Score</span>
                        <span className="output-value positive">
                          {(
                            agentResults.validator_openai.factual_score * 100
                          ).toFixed(1)}
                          %
                        </span>
                      </div>
                    )}
                    {agentResults.validator_gemini && (
                      <div className="output-item">
                        <span className="output-label">Gemini Score</span>
                        <span className="output-value positive">
                          {(
                            agentResults.validator_gemini.coherence_score * 100
                          ).toFixed(1)}
                          %
                        </span>
                      </div>
                    )}
                    {agentResults.consensus && (
                      <div className="output-item">
                        <span className="output-label">Consensus</span>
                        <span className="output-value positive">
                          {(
                            agentResults.consensus.consensus_score * 100
                          ).toFixed(1)}
                          %
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {finalResult && (
                <div className="final-comparison">
                  <div className="section-header">
                    <div className="section-title">Final Result Comparison</div>
                    <div className="section-line"></div>
                  </div>
                  <div className="comparison-grid">
                    <div className="comparison-card">
                      <div className="card-header">
                        <div className="card-title">Input</div>
                      </div>
                      <div className="card-content">{userMessage}</div>
                    </div>
                    <div className="comparison-card">
                      <div className="card-header">
                        <div className="card-title">Original Output</div>
                      </div>
                      <div className="card-content">
                        {finalResult.original_response || aiResponse}
                      </div>
                    </div>
                    <div className="comparison-card highlight">
                      <div className="card-header">
                        <div className="card-title">Corrected Output</div>
                      </div>
                      <div className="card-content corrected">
                        {finalResult.corrected_response}
                      </div>
                    </div>
                  </div>
                  <div className="final-metrics">
                    <div className="metric-item">
                      <span className="metric-label">Confidence</span>
                      <span className="metric-value">
                        {((finalResult.confidence || 0) * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="metric-item">
                      <span className="metric-label">Status</span>
                      <span
                        className={`metric-value ${finalResult.final_status || finalResult.status}`}
                      >
                        {(finalResult.final_status || finalResult.status || "")
                          .toUpperCase()
                          .replace("_", " ")}
                      </span>
                    </div>
                  </div>
                  {finalResult.retrieved_documents?.length > 0 && (
                    <div className="retrieved-docs">
                      <div className="section-header">
                        <div className="section-title">Retrieved Documents</div>
                        <div className="section-line"></div>
                      </div>
                      <div className="docs-grid">
                        {finalResult.retrieved_documents.map((doc, idx) => (
                          <div key={idx} className="doc-card">
                            <div className="doc-header">
                              <span className="doc-number">#{idx + 1}</span>
                              <span className="doc-similarity">
                                {(doc.similarity_score * 100).toFixed(1)}%
                              </span>
                            </div>
                            <div className="doc-content">
                              <div className="doc-question">
                                <strong>Q:</strong> {doc.user_message}
                              </div>
                              <div className="doc-answer">
                                <strong>A:</strong> {doc.ai_response}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="evaluation-section">
            <div className="section-header">
              <div className="section-title">Model Evaluation Metrics</div>
              <div className="section-line"></div>
            </div>
            <div className="dataset-info">
              <div className="dataset-grid">
                <div className="dataset-item">
                  <span className="dataset-label">Total Samples</span>
                  <span className="dataset-value">151</span>
                </div>
                <div className="dataset-item">
                  <span className="dataset-label">Features</span>
                  <span className="dataset-value">1536</span>
                </div>
                <div className="dataset-item">
                  <span className="dataset-label">Hallucination Positive</span>
                  <span className="dataset-value">
                    73 <span>(48.3%)</span>
                  </span>
                </div>
                <div className="dataset-item">
                  <span className="dataset-label">Bias Positive</span>
                  <span className="dataset-value">
                    61 <span>(40.4%)</span>
                  </span>
                </div>
              </div>
            </div>
            <div className="eval-grid">
              {["hallucination", "bias"].map((k) => (
                <div key={k} className="eval-card">
                  <div className="eval-header">
                    <div className="eval-title">{MODEL_METRICS[k].name}</div>
                    <div className="eval-accuracy">
                      <span className="accuracy-label">Accuracy</span>
                      <span className="accuracy-value">
                        {(MODEL_METRICS[k].accuracy * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div className="eval-body">
                    <table className="metrics-table">
                      <thead>
                        <tr>
                          <th>Class</th>
                          <th>Precision</th>
                          <th>Recall</th>
                          <th>F1-Score</th>
                          <th>Support</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(MODEL_METRICS[k].metrics).map(
                          ([c, m]) => (
                            <tr key={c}>
                              <td>{c}</td>
                              <td className="metric-highlight">
                                {m.precision.toFixed(2)}
                              </td>
                              <td className="metric-highlight">
                                {m.recall.toFixed(2)}
                              </td>
                              <td className="metric-highlight">
                                {m.f1.toFixed(2)}
                              </td>
                              <td>{m.support}</td>
                            </tr>
                          ),
                        )}
                      </tbody>
                    </table>
                    <div className="confusion-section">
                      <div className="confusion-title">Confusion Matrix</div>
                      <div className="confusion-matrix">
                        <div className="matrix-label-row">
                          <div className="matrix-label">Predicted</div>
                        </div>
                        <div className="matrix-label-row">
                          {MODEL_METRICS[k].labels.map((l, i) => (
                            <div key={i} className="matrix-label">
                              {l}
                            </div>
                          ))}
                        </div>
                        {MODEL_METRICS[k].confusionMatrix.map((row, ri) => (
                          <div key={ri} className="matrix-row">
                            <div className="matrix-row-label">
                              {ri === 0 ? "Actual " : ""}
                              {MODEL_METRICS[k].labels[ri]}
                            </div>
                            <div className="matrix-cells">
                              {row.map((cell, ci) => (
                                <div
                                  key={ci}
                                  className={`matrix-cell ${ri === ci ? "diagonal" : cell > 0 ? "error" : "off-diagonal"}`}
                                >
                                  {cell}
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="model-stats">
                      <div className="stat-row">
                        <span className="stat-label">Support Vectors</span>
                        <span className="stat-value">
                          {MODEL_METRICS[k].supportVectors}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default App;
