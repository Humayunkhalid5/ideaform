"use client";

import { Check, Copy } from "lucide-react";
import { useEffect, useState } from "react";

let counter = 0;

function useDarkTheme(): boolean {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const root = document.documentElement;
    const update = () => setDark(root.classList.contains("dark"));
    update();
    const observer = new MutationObserver(update);
    observer.observe(root, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);
  return dark;
}

/**
 * Renders Mermaid code to SVG in the browser. Mermaid is loaded only when a diagram is
 * shown, runs with securityLevel "strict", and follows the light/dark theme. If the code
 * cannot be drawn, the source is shown instead so nothing is lost.
 */
export function MermaidDiagram({ code }: { code: string }) {
  const dark = useDarkTheme();
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const id = `mermaid-${++counter}`;
    (async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: "strict",
          theme: dark ? "dark" : "neutral",
          fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
          flowchart: { curve: "basis", htmlLabels: false },
        });
        const result = await mermaid.render(id, code);
        if (!cancelled) {
          setSvg(result.svg);
          setError(null);
        }
      } catch (err) {
        document.getElementById(`d${id}`)?.remove(); // mermaid leaves its scratch node on errors
        if (!cancelled) {
          setSvg(null);
          setError(err instanceof Error ? err.message : "This diagram could not be drawn.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [code, dark]);

  async function copy() {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <figure className="group/diagram relative my-4 overflow-hidden rounded-lg border border-line bg-surface">
      <button
        type="button"
        onClick={copy}
        className="absolute right-2 top-2 z-10 inline-flex h-7 items-center gap-1 rounded-md border border-line bg-surface px-2 text-[11px] text-muted opacity-0 transition-opacity duration-150 hover:text-ink focus-visible:opacity-100 group-hover/diagram:opacity-100"
        aria-label="Copy Mermaid source"
      >
        {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
        {copied ? "Copied" : "Mermaid"}
      </button>
      {svg ? (
        <div
          className="overflow-x-auto p-4 [&_svg]:mx-auto [&_svg]:h-auto [&_svg]:max-w-full"
          // Mermaid output, rendered with securityLevel "strict"
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      ) : error ? (
        <div className="flex flex-col gap-2 p-4">
          <p className="text-[12px] text-warning">This diagram could not be drawn: {error.split("\n")[0]}</p>
          <pre className="overflow-x-auto rounded-md bg-surface-soft p-3 font-mono text-[11.5px] text-ink">{code}</pre>
        </div>
      ) : (
        <div className="h-40 animate-pulse bg-surface-soft" aria-label="Drawing diagram" />
      )}
    </figure>
  );
}
