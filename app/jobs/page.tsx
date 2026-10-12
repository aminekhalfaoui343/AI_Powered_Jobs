import Link from "next/link";
import { ArrowLeft, Fingerprint } from "lucide-react";
import { JobList } from "@/components/jobs/JobList";

export default function JobsPage() { return <main className="section"><div className="shell"><Link href="/" className="text-link"><ArrowLeft size={15} /> Back to search</Link><div className="section-heading" style={{ marginTop: 50 }}><div><span className="eyebrow">Job library</span><h1>Processed opportunities</h1></div><p>Structured roles from your searches, ready to review.</p></div><div className="library-note"><Fingerprint size={20} /><span>The current search endpoint returns queue metrics rather than individual job IDs. This library is ready for those records when the API exposes them.</span></div><JobList jobs={[]} /></div></main>; }