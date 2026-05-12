import { NavLink, useLocation } from "react-router-dom";

const tabs = [
  { to: "/upload", label: "Upload", num: "01" },
  { to: "/analyse", label: "Tailor", num: "02" },
  { to: "/dashboard", label: "Applications", num: "03" },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation();
  const showMasthead = pathname === "/" || pathname.startsWith("/upload");

  return (
    <div className="min-h-screen flex flex-col">
      {/* masthead — full hero on landing/upload, compact bar elsewhere */}
      <header className="relative">
        {showMasthead ? (
          <div className="max-w-[1400px] mx-auto px-8 pt-10 pb-8 flex flex-col md:flex-row md:items-end md:justify-between gap-8">
            <div className="reveal reveal-1">
              <div className="eyebrow mb-3 flex items-center gap-2">
                <Logo />
                <span>ResumeFit</span>
              </div>
              <h1 className="display text-[clamp(3rem,7vw,6rem)] leading-[0.95]">
                <span className="grad-text">Apply</span>{" "}
                <span className="ital text-text/90">smarter,</span>
                <br />
                <span className="text-text">not</span>{" "}
                <span className="ital text-mint">harder</span>
                <span className="text-mint">.</span>
              </h1>
              <p className="mt-5 text-[15px] leading-relaxed text-dim max-w-md">
                Drop your résumé in once. An AI pipeline reads each posting,
                scores the fit with semantic retrieval, and ships a tailored
                résumé and cover letter — every step streamed live, start to
                finish in about 20&nbsp;seconds.
              </p>
            </div>
            <Nav />
          </div>
        ) : (
          <div className="max-w-[1400px] mx-auto px-8 pt-5 pb-4 flex items-center justify-between gap-6">
            <NavLink to="/" className="eyebrow flex items-center gap-2 hover:text-mint transition-colors">
              <Logo />
              <span>ResumeFit</span>
            </NavLink>
            <Nav />
          </div>
        )}
        <div className="max-w-[1400px] mx-auto px-8">
          <div className="div-grad" />
        </div>
      </header>

      <main className="max-w-[1400px] mx-auto w-full px-8 py-12 flex-1 reveal reveal-3">
        {children}
      </main>

      <footer className="border-t border-white/5 mt-auto">
        <div className="max-w-[1400px] mx-auto px-8 py-5 flex items-center justify-between font-mono text-[11px] uppercase tracking-widest2 text-muted">
          <span>© {new Date().getFullYear()} ResumeFit · LangGraph + React</span>
          <span className="text-dim">runs locally · your data never leaves this machine</span>
        </div>
      </footer>
    </div>
  );
}

function Nav() {
  return (
    <nav className="glass px-2 py-2 flex items-center gap-1 self-start md:self-end reveal reveal-2">
      {tabs.map((t) => (
        <NavLink
          key={t.to}
          to={t.to}
          className={({ isActive }) =>
            ["nav-link flex items-center gap-2", isActive ? "active" : ""].join(" ")
          }
        >
          {({ isActive }) => (
            <>
              <span className={isActive ? "text-obsidian/60" : "text-mint/80"}>
                {t.num}
              </span>
              <span>{t.label}</span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}

function Logo() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      className="text-mint"
    >
      <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.2" />
      <circle cx="7" cy="7" r="2.2" fill="currentColor" />
      <path d="M7 1 V13 M1 7 H13" stroke="currentColor" strokeWidth="0.6" opacity="0.5" />
    </svg>
  );
}
