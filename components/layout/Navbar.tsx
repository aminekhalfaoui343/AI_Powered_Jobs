"use client";

import Link from "next/link";
import { Menu, Sparkles, X } from "lucide-react";
import { useState } from "react";

export function Navbar() {
  const [open, setOpen] = useState(false);
  return (
    <header className="site-header">
      <div className="shell nav-inner">
        <Link href="/" className="brand" onClick={() => setOpen(false)}>
          <span className="brand-mark"><Sparkles size={17} strokeWidth={2} /></span>
          <span>Glorea <strong>Career</strong><em> AI</em></span>
        </Link>
        <button className="mobile-menu" aria-label="Toggle navigation" onClick={() => setOpen((value) => !value)}>
          {open ? <X size={21} /> : <Menu size={21} />}
        </button>
        <nav className={open ? "main-nav is-open" : "main-nav"}>
          <Link href="/" onClick={() => setOpen(false)}>Search</Link>
          <Link href="/jobs" onClick={() => setOpen(false)}>Jobs</Link>
          <a href="#about" onClick={() => setOpen(false)}>About</a>
        </nav>
        <div className="nav-status"><span /> Intelligence online</div>
      </div>
    </header>
  );
}