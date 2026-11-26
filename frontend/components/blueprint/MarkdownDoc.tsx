"use client";

import type { ComponentProps } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";

import { MermaidDiagram } from "./MermaidDiagram";

interface HastNode {
  type: string;
  tagName?: string;
  value?: string;
  properties?: { className?: string[] | string };
  children?: HastNode[];
}

function mermaidSource(node: HastNode | undefined): string | null {
  const code = node?.children?.find((c) => c.type === "element" && c.tagName === "code");
  const cls = code?.properties?.className;
  const classes = Array.isArray(cls) ? cls : typeof cls === "string" ? [cls] : [];
  if (!code || !classes.includes("language-mermaid")) return null;
  return (code.children ?? []).map((c) => c.value ?? "").join("").trim();
}

/** A generated document: GitHub-flavoured Markdown with Mermaid code blocks drawn as diagrams. */
export function MarkdownDoc({ content, className }: { content: string; className?: string }) {
  return (
    <div className={cn("if-doc", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          pre({ node, children, ...props }: ComponentProps<"pre"> & { node?: HastNode }) {
            const source = mermaidSource(node);
            if (source) return <MermaidDiagram code={source} />;
            return <pre {...props}>{children}</pre>;
          },
          a({ node: _node, ...props }: ComponentProps<"a"> & { node?: unknown }) {
            return <a {...props} target="_blank" rel="noopener noreferrer" />;
          },
          table({ node: _node, ...props }: ComponentProps<"table"> & { node?: unknown }) {
            return (
              <div className="my-4 overflow-x-auto rounded-lg border border-line">
                <table {...props} />
              </div>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
