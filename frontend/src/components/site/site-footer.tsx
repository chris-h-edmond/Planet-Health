import Link from "next/link";

import { PlanetHealthLogo } from "@/components/brand/planet-health-logo";

const FOOTER_SECTIONS = [
  {
    title: "Product",
    links: [
      { label: "Features", href: "/#features" },
      { label: "How it works", href: "/#how-it-works" },
      { label: "Technology", href: "/#about" },
      { label: "Dashboard", href: "/dashboard" },
    ],
  },
  {
    title: "Account",
    links: [
      { label: "Sign in", href: "/login" },
      { label: "Create account", href: "/register" },
      { label: "Analysis history", href: "/dashboard/history" },
      { label: "Settings", href: "/dashboard/settings" },
    ],
  },
];

export function SiteFooter() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-border bg-card/40">
      <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6">
        <div className="grid gap-10 md:grid-cols-[1.4fr_1fr_1fr]">
          <div className="space-y-4">
            <PlanetHealthLogo />
            <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">
              An AI-assisted plant monitoring platform that turns a single
              photograph into stress classification and growth estimates.
            </p>
            <p className="text-xs leading-relaxed text-muted-foreground/80">
              Built on experimental research models. Results are estimates and
              do not replace direct plant inspection.
            </p>
          </div>

          {FOOTER_SECTIONS.map((section) => (
            <div key={section.title}>
              <h3 className="text-sm font-semibold text-foreground">
                {section.title}
              </h3>
              <ul className="mt-4 space-y-2.5">
                {section.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-col gap-3 border-t border-border pt-6 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p>© {year} Planet Health. All rights reserved.</p>
          <p>
            Computer vision for greenhouse monitoring · PyTorch · PostgreSQL
          </p>
        </div>
      </div>
    </footer>
  );
}
