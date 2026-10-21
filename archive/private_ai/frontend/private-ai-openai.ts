import type { PrivateAiCompanyReport } from "../types";

export const privateAiOpenai: PrivateAiCompanyReport = {
  company: "OpenAI",
  command: "ai openai",
  updated: "01 JUL 2026",
  dataQuality: "Reported / Estimated / Low confidence where disclosure is incomplete",
  analysisMode: "Private AI Company Intelligence",
  summary:
    "OpenAI is analyzed as a frontier private AI platform, not as a public operating company. The evidence base points to unusual revenue scale, strong consumer and developer distribution, substantial enterprise momentum, and heavy compute dependence.",
  scale: [
    { Metric: "Annual Recurring Revenue", Value: "$12B annualized revenue run rate", Confidence: "Reported" },
    { Metric: "Estimated Annual Revenue", Value: "$3.7B in 2024 revenue", Confidence: "Reported" },
    { Metric: "Revenue Run Rate", Value: "$12B", Confidence: "Reported" },
    { Metric: "Enterprise Revenue %", Value: "Unavailable", Confidence: "Unavailable" },
    { Metric: "Consumer Revenue %", Value: "Unavailable", Confidence: "Unavailable" },
    { Metric: "API Revenue %", Value: "Unavailable", Confidence: "Unavailable" }
  ],
  adoption: [
    { Metric: "Enterprise customers", Value: "Millions of business users reported", Confidence: "Reported" },
    { Metric: "Developer adoption", Value: "Broad API and developer ecosystem usage", Confidence: "Reported" },
    { Metric: "Consumer adoption", Value: "ChatGPT remains a mass-market AI assistant", Confidence: "Reported" },
    { Metric: "Retention", Value: "Unavailable", Confidence: "Unavailable" },
    { Metric: "Expansion", Value: "Unavailable", Confidence: "Unavailable" }
  ],
  product: [
    { Area: "Flagship model", Evidence: "GPT-4o / GPT-4.1 family; o-series reasoning models", Confidence: "Reported" },
    { Area: "Enterprise position", Evidence: "Horizontal enterprise AI platform", Confidence: "Reported" },
    { Area: "Consumer position", Evidence: "Mass-market AI assistant", Confidence: "Reported" },
    { Area: "API competitiveness", Evidence: "Core frontier API provider", Confidence: "Reported" },
    { Area: "Benchmark position", Evidence: "Frontier position varies by model and benchmark", Confidence: "Low confidence" }
  ],
  infrastructure: [
    { Metric: "GPU access", Value: "Large-scale access through strategic cloud and infrastructure partners", Confidence: "Reported" },
    { Metric: "Cloud partnerships", Value: "Microsoft Azure and additional infrastructure initiatives", Confidence: "Reported" },
    { Metric: "Estimated compute spending", Value: "Multi-billion-dollar annual commitments", Confidence: "Estimated" },
    { Metric: "Compute dependency", Value: "Core constraint on model quality, latency, and gross margin", Confidence: "Estimated" }
  ],
  capital: [
    { Metric: "Funding raised", Value: "Tens of billions across strategic and financial rounds", Confidence: "Reported" },
    { Metric: "Cash position", Value: "Unavailable", Confidence: "Unavailable" },
    { Metric: "Known investors", Value: "Microsoft, SoftBank, Thrive, Coatue, Altimeter, others", Confidence: "Reported" },
    { Metric: "Expected funding needs", Value: "Continued external or partner-financed infrastructure likely", Confidence: "Estimated" }
  ],
  valuation: [
    { Metric: "Latest valuation", Value: "$300B post-money in 2025 financing", Confidence: "Reported" },
    { Metric: "Previous valuation", Value: "$157B in 2024 financing", Confidence: "Reported" },
    { Metric: "ARR multiple", Value: "25.0x", Confidence: "Estimated" },
    { Metric: "Revenue multiple", Value: "81.1x", Confidence: "Estimated" }
  ],
  competitors: [
    { Competitor: "Anthropic", Position: "Enterprise and developer-focused frontier lab" },
    { Competitor: "Google DeepMind", Position: "Integrated model research and platform distribution" },
    { Competitor: "Meta", Position: "Open model ecosystem and consumer distribution" },
    { Competitor: "xAI", Position: "Compute-heavy challenger with X distribution" },
    { Competitor: "Perplexity", Position: "AI-native search and research workflow challenger" }
  ],
  strengthen: [
    "Enterprise ARR accelerates with disclosed retention and expansion evidence",
    "API usage expands without visible gross-margin deterioration",
    "Inference cost per query declines",
    "Compute partnerships expand on terms that preserve strategic flexibility",
    "Major enterprise or government wins become recurring revenue rather than pilots"
  ],
  weaken: [
    "Revenue growth slows from the current run-rate trajectory",
    "Enterprise churn rises or usage-based expansion weakens",
    "Capital requirements increase faster than revenue",
    "Model competitiveness declines on reasoning, coding, or multimodal benchmarks",
    "Regulatory or governance restrictions limit product deployment"
  ],
  finalInterpretation:
    "OpenAI continues to demonstrate unusual scale for a private AI company, supported by consumer distribution, enterprise conversion, API adoption, and frontier-model perception. The valuation embeds expectations for continued execution across enterprise adoption, model performance, and infrastructure scaling. The primary risks remain compute intensity, capital requirements, governance complexity, and intensifying competition."
};
