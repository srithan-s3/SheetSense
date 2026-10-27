import {
  ArrowRight,
  ChartNoAxesCombined,
  Check,
  FileSpreadsheet,
  Layers3,
  ShieldCheck,
  Sparkles,
  Upload,
  WandSparkles,
} from "lucide-react";
import { Logo, ThemeButton } from "../components/UI";
import { SamplePicker } from "../components/SamplePicker";
import type { Sample } from "../types";
export function Landing({
  onStart,
  onSample,
  dark,
  toggleTheme,
  busy,
}: {
  onStart: () => void;
  onSample: (sample: Sample) => void;
  dark: boolean;
  toggleTheme: () => void;
  busy: boolean;
}) {
  return (
    <div className="landing">
      <header className="landing-nav">
        <Logo onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })} />
        <nav aria-label="Main navigation">
          <a href="#features">Features</a>
          <a href="#how-it-works">How it works</a>
          <a href="#samples">Sample datasets</a>
        </nav>
        <div className="nav-actions">
          <ThemeButton dark={dark} toggle={toggleTheme} />
          <button className="button primary small" onClick={onStart}>
            Open workspace
            <ArrowUpRightIcon />
          </button>
        </div>
      </header>
      <main id="main-content">
        <section className="hero">
          <div className="hero-copy">
            <div className="hero-badge">
              <span>
                <Sparkles size={14} />
              </span>{" "}
              LESS SPREADSHEET. MORE PERSPECTIVE.
            </div>
            <h1>
              Turn Your
              <br />
              Spreadsheets
              <br />
              Into <span>Insights.</span>
            </h1>
            <p>
              Your data has a story to tell. Upload a spreadsheet and discover
              the patterns, trends, and answers hiding in the rows.
            </p>
            <div className="hero-actions">
              <button className="button primary" onClick={onStart}>
                Analyze Your Data
                <ArrowRight size={18} />
              </button>
              <a className="button secondary" href="#samples">
                Explore Sample Dataset
              </a>
            </div>
            <div className="hero-benefits">
              <span>
                <Check size={15} />
                No account needed
              </span>
              <span>
                <Check size={15} />
                No AI API required
              </span>
            </div>
            <div className="file-support">
              <FileSpreadsheet size={16} />
              <span>
                Works with <strong>.xlsx</strong>
                <strong>.xls</strong>
                <strong>.csv</strong>
              </span>
            </div>
          </div>
          <div className="hero-visual">
            <div className="preview-window">
              <div className="preview-window-bar">
                <div className="window-dots">
                  <i />
                  <i />
                  <i />
                </div>
                <span>YOUR NEXT AHA MOMENT</span>
                <Layers3 size={14} />
              </div>
              <div className="illustration-body">
                <div className="illustration-top">
                  <div>
                    <small>WORKSPACE / OVERVIEW</small>
                    <h3>A clearer view of your data</h3>
                  </div>
                  <span className="tag">Example layout</span>
                </div>
                <div className="illustration-kpis">
                  <div>
                    <span>Records</span>
                    <strong>Find the big picture</strong>
                    <i />
                  </div>
                  <div>
                    <span>Metrics</span>
                    <strong>See what matters</strong>
                    <i />
                  </div>
                  <div>
                    <span>Quality</span>
                    <strong>Know your data</strong>
                    <i />
                  </div>
                </div>
                <div className="illustration-charts">
                  <div className="illustration-bars">
                    <span>Compare categories</span>
                    <div className="bar-plot">
                      {[42, 68, 52, 88, 65, 96, 74].map((height, index) => (
                        <i key={index} style={{ height: `${height}%` }} />
                      ))}
                    </div>
                    <div className="plot-labels">
                      <i />
                      <i />
                      <i />
                      <i />
                      <i />
                      <i />
                      <i />
                    </div>
                  </div>
                  <div className="illustration-donut">
                    <span>Understand the whole</span>
                    <div className="donut">
                      <div>
                        <ChartNoAxesCombined size={25} />
                        <small>Clarity at a glance</small>
                      </div>
                    </div>
                    <div className="mini-legend">
                      <i />
                      <i />
                      <i />
                    </div>
                  </div>
                </div>
                <div className="illustration-insight">
                  <span>
                    <Sparkles size={19} />
                  </span>
                  <div>
                    <strong>From rows to revelations</strong>
                    <p>
                      Meaningful charts. Understandable insights. All in one
                      place.
                    </p>
                  </div>
                </div>
              </div>
            </div>
            <div className="visual-caption">
              <span className="status-dot" />
              Illustrative preview · your dashboard adapts to your actual data
            </div>
            <div className="floating-file">
              <span>
                <FileSpreadsheet size={23} />
              </span>
              <div>
                <strong>From spreadsheet</strong>
                <small>to a fresh perspective</small>
              </div>
              <Check size={16} />
            </div>
          </div>
        </section>
        <section className="value-strip">
          <span>
            LESS MANUAL WORK.
            <br />
            <strong>MORE MEANINGFUL ANSWERS.</strong>
          </span>
          <div>
            <ChartNoAxesCombined size={21} />
            Automatic visualizations
          </div>
          <div>
            <ShieldCheck size={21} />
            Thoughtful data quality checks
          </div>
          <div>
            <FileSpreadsheet size={21} />
            Reports ready to share
          </div>
        </section>
        <section className="features-section" id="features">
          <div className="section-heading">
            <div>
              <span className="eyebrow">A SMARTER WAY TO EXPLORE</span>
              <h2>All the insight. None of the busywork.</h2>
              <p>From an unfamiliar file to an understandable story.</p>
            </div>
          </div>
          <div className="feature-grid">
            {[
              {
                icon: ChartNoAxesCombined,
                title: "Charts that make sense",
                text: "Your columns guide the visuals. Trends, comparisons, and distributions appear when your data supports them.",
                label: "AUTOMATIC ANALYTICS",
              },
              {
                icon: WandSparkles,
                title: "Go beyond the obvious",
                text: "Discover useful statistics, explore custom charts, and narrow the picture with filters that update everything.",
                label: "YOUR QUESTIONS, ANSWERED",
              },
              {
                icon: ShieldCheck,
                title: "Confidence in every row",
                text: "Spot missing values, duplicates, and unusual data. Preview optional cleaning changes before you apply them.",
                label: "QUALITY BUILT IN",
              },
            ].map(({ icon: Icon, title, text, label }) => (
              <article className="feature-card" key={title}>
                <span className="feature-icon">
                  <Icon size={23} />
                </span>
                <small>{label}</small>
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>
        <section className="how-section" id="how-it-works">
          <div>
            <span className="eyebrow">FROM FILE TO FOCUS</span>
            <h2>
              Three steps.
              <br />A whole new perspective.
            </h2>
            <p>
              No formulas to memorize.
              <br />
              No dashboard to build from scratch.
            </p>
            <button className="text-button accent" onClick={onStart}>
              Let’s open your spreadsheet <ArrowRight size={16} />
            </button>
          </div>
          <div className="steps">
            {[
              {
                title: "Bring your data",
                text: "Drop an Excel or CSV file, choose a worksheet, and preview the records.",
                icon: Upload,
              },
              {
                title: "Let the patterns emerge",
                text: "Get useful metrics, automatically selected charts, and clear statistical insights.",
                icon: Sparkles,
              },
              {
                title: "Explore. Export. Understand.",
                text: "Refine your view, build a chart, or take a PDF report with you.",
                icon: ChartNoAxesCombined,
              },
            ].map(({ title, text, icon: Icon }, index) => (
              <div className="step" key={title}>
                <span className="step-number">0{index + 1}</span>
                <div>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </div>
                <Icon size={23} />
              </div>
            ))}
          </div>
        </section>
        <SamplePicker onSelect={onSample} busy={busy} />
        <section className="landing-cta">
          <div>
            <span className="eyebrow">YOUR DATA IS THE STARTING POINT</span>
            <h2>Make your next spreadsheet make sense.</h2>
            <p>Bring the rows. We’ll help you find the story.</p>
          </div>
          <button className="button primary" onClick={onStart}>
            Analyze Your Data
            <ArrowRight size={18} />
          </button>
        </section>
      </main>
      <footer className="landing-footer">
        <Logo onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })} />
        <p>
          A Web Programming project. Built with curiosity, powered by your data.
        </p>
        <span>React + Python · Open source</span>
      </footer>
    </div>
  );
}
function ArrowUpRightIcon() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M7 17 17 7M7 7h10v10" />
    </svg>
  );
}
