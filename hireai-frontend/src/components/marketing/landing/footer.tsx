import Link from "next/link";

const links = [
  { href: "/privacy", label: "Privacy" },
  { href: "/terms", label: "Terms" },
  { href: "/docs", label: "Docs" },
  { href: "mailto:hireaidigitalemployee@gmail.com", label: "Contact" },
];

export function Footer() {
  return (
    <footer className="border-t border-border bg-background">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center gap-6 sm:flex-row sm:justify-between">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-navy text-xs font-bold text-white">
              H
            </div>
            <span className="text-sm font-bold text-text">HireAI</span>
          </div>

          {/* Links */}
          <div className="flex flex-wrap items-center justify-center gap-6">
            {links.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                className="text-sm text-text-3 transition-colors hover:text-text"
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* Copyright */}
          <p className="text-xs text-text-4">
            &copy; 2025 HireAI. All rights reserved.
          </p>
        </div>

        <div className="mt-4 text-center">
          <a
            href="mailto:hireaidigitalemployee@gmail.com"
            className="text-xs text-text-4 hover:text-text-3"
          >
            hireaidigitalemployee@gmail.com
          </a>
        </div>
      </div>
    </footer>
  );
}
