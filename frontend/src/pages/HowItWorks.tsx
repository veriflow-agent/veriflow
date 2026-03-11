// src/pages/HowItWorks.tsx
import { Link } from "react-router-dom";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

const steps = [
  "Choose your mode -- select the analysis type that fits your needs",
  "Paste your content -- article text, LLM output with links, or enter a URL",
  "Click Analyze -- VeriFlow does the rest",
  "Review results -- explore detailed findings with source links",
];

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
              VeriFlow detects AI errors and hallucinations while uncovering
              manipulation, deception, and bias in any text -- LLM-generated or
              human-written.
            </p>
          </div>

          {/* What It Is */}
          <Section title="What It Is">
            <p className="text-muted-foreground leading-relaxed mb-4">
              VeriFlow is a comprehensive risk-reduction and verification platform
              that detects hallucinations, unsupported or overstated claims,
              citation mismatches, missing context, fabricated narratives, logical
              inconsistencies, bias, deception signals, and manipulative framing
              in large language model outputs -- and in any written text -- through
              a multi-layered analysis system.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              VeriFlow eliminates the need to manually check every claim. Instead
              of reviewing each statement yourself, it automatically verifies
              claims against sources, analyzes narrative structure, and flags risks
              in seconds. It detects fake news patterns, identifies manipulation
              and deceptive language, and highlights where framing may distort
              meaning or intent.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              The platform includes multiple integrated modules. LLM Output
              Verification cross-checks AI-generated answers against their cited
              sources to confirm that each claim is actually supported, flagging
              unsupported statements, exaggerations, citation mismatches, and
              missing context. Research shows that retrieval-augmented,
              source-grounded workflows can reduce hallucination rates by over 40%
              in some settings, and in internal benchmarking VeriFlow detects
              approximately 80-90% of incorrect or unsupported statements when
              claims are directly checkable against cited material.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Comprehensive Analysis performs full-spectrum verification,
              evaluating source credibility, author reliability, and content
              quality. Key Claims Analysis isolates and rigorously verifies the
              most important arguments. Bias Analysis detects political or
              ideological slant. Deception Detection identifies linguistic markers
              of misinformation and coordinated narratives. Manipulation Check
              surfaces agenda-driven framing, fact distortion, cherry-picking, and
              causal exaggeration. A forthcoming Full Fact-Check module extends
              verification beyond cited links to broader independent corroboration.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              Together, these layers create a complete verification workflow --
              source validation, factual reliability assessment, fake detection,
              bias and deception analysis, manipulation detection, and reasoning
              control -- transforming AI outputs, articles, and texts into
              auditable, risk-assessed documents suitable for professional and
              high-stakes environments.
            </p>
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

        </div>
      </main>

      <Footer />
    </div>
  );
};

export default HowItWorks;