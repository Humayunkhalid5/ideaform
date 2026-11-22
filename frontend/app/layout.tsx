import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Ideaform",
  description: "AI idea analysis: evaluation, research, and blueprint generation.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
