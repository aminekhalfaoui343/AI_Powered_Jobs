import Image from "next/image";

export function Footer() {
  return <footer className="footer"><div className="shell footer-inner"><span className="footer-brand"><Image src="/glorea-career-logo.png" alt="" width={24} height={24} className="brand-logo brand-logo-small" /> Glorea Career <b>AI</b></span><span>International opportunity, intelligently organized.</span></div></footer>;
}