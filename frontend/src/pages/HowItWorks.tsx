// src/pages/HowItWorks.tsx
import { Link } from "react-router-dom";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

const modes = [
  {
    title: "LLM Output Verification",
    bestFor: "Confirming that AI summaries match their sources",
    description:
      "Retrieves the original sources cited by an LLM and compares them with the generated output to confirm the content is accurate and faithful. Detects misinterpretations, missing context, selective quoting, and hallucinated claims.",
  },
  {
    title: "Key Claims Analysis",
    bestFor: "Fast validation of the main points",
    description:
      "Identifies the 2-3 most important factual claims in a text and verifies each one against credible sources. Ideal for quick checks of headlines, short articles, or social media posts.",
  },
  {
    title: "Bias Analysis",
    bestFor: "Identifying framing and ideological slant",
    description:
      "Analyzes political and ideological positioning through language patterns, framing choices, and narrative emphasis -- helping assess how perspective may shape interpretation even when factual claims appear correct.",
  },
  {
    title: "Manipulation Detection",
    bestFor: "Detecting strategic distortion and misleading techniques",
    description:
      "Flags manipulation methods such as selective omission, context stripping, false equivalence, emotional framing, and other techniques used to distort perception and influence conclusions.",
  },
  {
    title: "Deception Detection",
    bestFor: "Identifying linguistic signals associated with deceptive communication",
    description:
      "Examines text for patterns commonly linked to deceptive messaging, including hedging, distancing language, excessive qualifiers, inconsistencies, and other linguistic markers.",
  },
  {
    title: "Comprehensive Analysis",
    bestFor: "Full-scope content risk assessment",
    description:
      "Runs an integrated review combining source verification, key claim validation, bias detection, manipulation analysis, and deception-signal detection to provide a complete reliability and risk profile of any text.",
  },
];

const comparisonRows = [
  [
    "Hidden system prompts set by company",
    "Custom prompts designed for objective analysis",
  ],
  [
    "Reflects creator's ideology",
    "Prompts focused purely on verification tasks",
  ],
  [
    '"Personality" and opinions baked in',
    "Strict, clinical instructions with no editorializing",
  ],
  [
    "High temperature = creative, unpredictable",
    "Low temperature = deterministic, fact-focused",
  ],
];

const tiers = [
  {
    name: "Tier 1 -- Primary Authority",
    description:
      "Official websites of entities mentioned, government sources, major news organizations (Reuters, AP, BBC, NYT), academic institutions, Wikipedia, verified social media accounts.",
  },
  {
    name: "Tier 2 -- Credible Secondary",
    description:
      "Established publications with editorial standards, industry publications, trade journals, professional review sites, reputable blogs with author credentials.",
  },
  {
    name: "Tier 3 -- Filtered Out",
    description:
      "Personal blogs without credentials, user-generated content, clickbait sites, sources with poor factual track records.",
  },
];

const steps = [
  "Choose your mode -- select the analysis type that fits your needs",
  "Paste your content -- article text, LLM output with links, or enter a URL",
  "Click Analyze -- VeriFlow does the rest",
  "Review results -- explore detailed findings with source links",
];

/* ------------------------------------------------------------------ */

const Section = ({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) => (
  <section className="mb-14">
    <h2 className="font-display text-2xl font-semibold mb-6 pb-3 border-b border-border">
      {title}
    </h2>
    {children}
  </section>
);

const HowItWorks = () => {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1">
        <div className="container max-w-3xl py-12 px-4">
          {/* Hero */}
          <div className="mb-14">
            <h1 className="font-display text-4xl md:text-5xl font-semibold mb-4">
              How It Works
            </h1>
            <p className="text-lg text-muted-foreground leading-relaxed">
              VeriFlow is a risk reduction and verification tool that checks
              LLM outputs against original sources and analyzes any text for
              bias, deception signals, manipulation patterns, and agenda-driven
              framing.
            </p>
          </div>

          {/* What It Is */}
          <Section title="What It Is">
            <p className="text-muted-foreground leading-relaxed mb-4">
              VeriFlow is designed for situations where inaccurate text can
              create legal, financial, regulatory, or reputational consequences.
              It works by comparing AI-generated or human-written content with
              the original source materials and checking whether the key
              statements in the text are actually supported by what the sources
              say. It flags unsupported claims, incorrect or fabricated
              citations, missing context, selective quoting, and cases where the
              conclusion is not justified by the evidence provided.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              In addition to factual and source verification, VeriFlow performs
              deeper content analysis to detect bias and framing, identify
              manipulation patterns, and highlight linguistic signals associated
              with deception or disinformation-style writing. The output is
              presented as a structured assessment that can be reviewed by
              analysts, lawyers, compliance teams, researchers, or
              communications teams -- and used as documentation to support
              responsible decision-making and governance.
            </p>
          </Section>

          {/* Why AI Fact-Checking Needs a Different Approach */}
          <Section title="Why AI Fact-Checking Needs a Different Approach">
            <p className="text-muted-foreground leading-relaxed mb-4">
              When you ask ChatGPT or Claude to fact-check something, you're
              asking a system that was fine-tuned by a company with particular
              values, views, and business incentives. The AI's "opinions" aren't
              neutral -- they reflect choices made during training about what to
              emphasize, what to downplay, and how to frame contested topics.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              This isn't a flaw -- it's by design. Consumer AI products are built
              to be helpful, harmless, and engaging. But "helpful" often means
              telling you what the creator thinks you should hear.
            </p>

            <h3 className="text-lg font-semibold mt-8 mb-4">
              How VeriFlow Is Different
            </h3>
            <p className="text-muted-foreground leading-relaxed mb-5">
              VeriFlow accesses AI models directly through APIs, bypassing the
              pre-packaged system prompts of consumer products. This gives us
              complete control over how the AI behaves.
            </p>

            {/* Comparison table */}
            <div className="rounded-lg border border-border overflow-hidden mb-8">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-secondary/60">
                    <th className="text-left px-4 py-3 font-semibold">
                      Consumer Products
                    </th>
                    <th className="text-left px-4 py-3 font-semibold">
                      VeriFlow's API Approach
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonRows.map(([left, right], i) => (
                    <tr key={i} className="border-t border-border">
                      <td className="px-4 py-3 text-muted-foreground">
                        {left}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {right}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <h3 className="text-lg font-semibold mt-8 mb-4">
              Verification vs. Opinion
            </h3>
            <p className="text-muted-foreground leading-relaxed mb-3">
              LLMs are most prone to hallucination when asked to generate
              opinions, make predictions, or create content from scratch. But
              VeriFlow doesn't ask AI to <em>evaluate</em> what's true -- we ask
              it to <em>verify</em> claims against evidence.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-3">
              The difference is crucial:
            </p>
            <div className="pl-4 border-l-2 border-border space-y-2 mb-5">
              <p className="text-muted-foreground">
                <span className="font-medium text-foreground">
                  Opinion task:
                </span>{" "}
                "Is this article biased?" -- the AI must form a judgment
              </p>
              <p className="text-muted-foreground">
                <span className="font-medium text-foreground">
                  Verification task:
                </span>{" "}
                "Does Source A support Claim B? Quote the relevant text." -- the
                AI compares and reports
              </p>
            </div>
            <p className="text-muted-foreground leading-relaxed mb-4">
              By constraining AI to structured verification tasks -- extracting
              claims, finding sources, comparing text, identifying discrepancies
              -- we minimize the space for hallucination or bias. The AI isn't
              deciding what's true; it's showing you what the evidence says.
            </p>

            <h3 className="text-lg font-semibold mt-8 mb-4">
              Built-In Transparency
            </h3>
            <p className="text-muted-foreground leading-relaxed mb-2">
              Every VeriFlow analysis includes the exact sources consulted,
              relevant quotes from those sources, confidence scores based on
              evidence strength, and full audit trails you can verify yourself.
            </p>
            <p className="text-muted-foreground leading-relaxed font-medium">
              We don't ask you to trust the AI. We give you the receipts.
            </p>
          </Section>

          {/* Six Analysis Modes */}
          <Section title="Six Analysis Modes">
            <div className="space-y-8">
              {modes.map((mode) => (
                <div key={mode.title}>
                  <h3 className="text-lg font-semibold mb-1">{mode.title}</h3>
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground mb-2">
                    Best for: {mode.bestFor}
                  </p>
                  <p className="text-muted-foreground leading-relaxed">
                    {mode.description}
                  </p>
                </div>
              ))}
            </div>
          </Section>

          {/* Technology */}
          <Section title="Technology">
            <h3 className="text-lg font-semibold mb-3">
              Multi-Agent Architecture
            </h3>
            <p className="text-muted-foreground leading-relaxed mb-8">
              VeriFlow uses a multi-agent system where specialized AI agents
              handle different tasks: the Fact Extractor identifies verifiable
              claims, the Query Generator creates search queries in multiple
              languages, the Credibility Filter evaluates source reliability, the
              Highlighter extracts relevant excerpts, the Fact Checker compares
              claims against evidence, the Bias Analyzer detects ideological
              lean, and the Manipulation Detector identifies distortion
              techniques.
            </p>

            <h3 className="text-lg font-semibold mb-3">
              Source Credibility System
            </h3>
            <p className="text-muted-foreground leading-relaxed mb-5">
              VeriFlow uses a three-tier credibility system. When sources
              conflict, Tier 1 always takes precedence.
            </p>

            <div className="space-y-4 mb-8">
              {tiers.map((tier) => (
                <div
                  key={tier.name}
                  className="rounded-lg border border-border bg-card p-4"
                >
                  <h4 className="font-semibold text-sm mb-1">{tier.name}</h4>
                  <p className="text-muted-foreground text-sm leading-relaxed">
                    {tier.description}
                  </p>
                </div>
              ))}
            </div>

            <h3 className="text-lg font-semibold mb-3">
              Real-Time Verification
            </h3>
            <p className="text-muted-foreground leading-relaxed mb-8">
              Unlike cached solutions, VeriFlow scrapes content fresh for every
              analysis. Sources reflect what's published now, not stale cached
              data.
            </p>

            <h3 className="text-lg font-semibold mb-3">
              Parallel Processing
            </h3>
            <p className="text-muted-foreground leading-relaxed">
              Complex analyses can involve dozens of claims and hundreds of
              sources. VeriFlow processes everything in parallel -- facts verified
              simultaneously, searches running concurrently, scraping in batches
              -- resulting in 60-70% faster processing than sequential methods.
            </p>
          </Section>

          {/* What You Get */}
          <Section title="What You Get">
            <p className="text-muted-foreground leading-relaxed mb-4">
              Every analysis includes confidence scores showing how well each
              claim is supported, source citations with links to the actual
              sources used, detailed reasoning explaining the assessment, and
              session reports with downloadable audit trails.
            </p>

            <h3 className="text-lg font-semibold mt-6 mb-4">
              Verification Categories
            </h3>
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <span className="inline-block mt-0.5 w-2.5 h-2.5 rounded-full bg-[hsl(var(--score-high))] shrink-0" />
                <p className="text-muted-foreground">
                  <span className="font-medium text-foreground">
                    Verified (85-100%)
                  </span>{" "}
                  -- Strongly supported by credible sources
                </p>
              </div>
              <div className="flex items-start gap-3">
                <span className="inline-block mt-0.5 w-2.5 h-2.5 rounded-full bg-[hsl(var(--score-moderate))] shrink-0" />
                <p className="text-muted-foreground">
                  <span className="font-medium text-foreground">
                    Partially Verified (50-84%)
                  </span>{" "}
                  -- Some support, but with caveats or missing context
                </p>
              </div>
              <div className="flex items-start gap-3">
                <span className="inline-block mt-0.5 w-2.5 h-2.5 rounded-full bg-[hsl(var(--score-low))] shrink-0" />
                <p className="text-muted-foreground">
                  <span className="font-medium text-foreground">
                    Unverified (0-49%)
                  </span>{" "}
                  -- Contradicted by evidence or no credible support found
                </p>
              </div>
            </div>
          </Section>

          {/* Getting Started */}
          <Section title="Getting Started">
            <div className="space-y-4 mb-6">
              {steps.map((step, i) => (
                <div key={i} className="flex gap-4">
                  <span className="flex items-center justify-center w-7 h-7 rounded-full bg-primary text-primary-foreground text-sm font-semibold shrink-0">
                    {i + 1}
                  </span>
                  <p className="text-muted-foreground leading-relaxed pt-0.5">
                    {step}
                  </p>
                </div>
              ))}
            </div>
            <p className="text-muted-foreground">
              Analysis typically takes 1-3 minutes depending on content
              complexity.
            </p>
          </Section>

          {/* Powered By */}
          <Section title="Powered By">
            <div className="flex flex-wrap gap-3">
              {["GPT-4o", "LangChain", "Brave Search", "Browserless"].map(
                (tech) => (
                  <span
                    key={tech}
                    className="rounded-full border border-border bg-secondary/50 px-4 py-1.5 text-sm text-muted-foreground"
                  >
                    {tech}
                  </span>
                )
              )}
            </div>
          </Section>

          {/* CTA */}
          <div className="text-center pt-6 border-t border-border">
            <h3 className="text-xl font-semibold mb-2">Ready to verify?</h3>
            <p className="text-muted-foreground mb-6">
              Start analyzing in seconds.
            </p>
            <Link
              to="/"
              className="inline-block rounded-lg bg-primary px-8 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Try VeriFlow
            </Link>
            <p className="mt-8 text-sm italic text-muted-foreground">
              VeriFlow: Because the truth shouldn't be hard to find.
            </p>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default HowItWorks;