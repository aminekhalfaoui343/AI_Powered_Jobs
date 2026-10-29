"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import Image from "next/image";
import { Briefcase, LayoutDashboard, Radio, Search, X } from "lucide-react";

const links = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/search", label: "Search", icon: Search },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/sources", label: "Sources", icon: Radio },
];

export function Sidebar({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const pathname = usePathname();

  return (
    <>
      <button
        type="button"
        className={open ? "dash-overlay is-open" : "dash-overlay"}
        aria-label="Close menu"
        onClick={onClose}
      />
      <aside className={open ? "dash-sidebar is-open" : "dash-sidebar"}>
        <div className="dash-brand">
          <Image
            src="/glorea-career-logo.png"
            alt=""
            width={36}
            height={36}
            className="brand-logo"
          />
          <span>
            Glorea <strong>Career</strong>
            <em>AI</em>
          </span>
          <button type="button" className="dash-sidebar-close" onClick={onClose} aria-label="Close sidebar">
            <X size={18} />
          </button>
        </div>
        <nav className="dash-nav">
          {links.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={active ? "dash-nav-link is-active" : "dash-nav-link"}
                onClick={onClose}
              >
                <Icon size={16} />
                {label}
              </Link>
            );
          })}
        </nav>
        <p className="dash-sidebar-note">Extracted jobs persist in PostgreSQL. Redis is the live queue.</p>
      </aside>
    </>
  );
}
