/** Re-mounts on every tab change; the project header (layout) stays in place. */
export default function ProjectTabTemplate({ children }: { children: React.ReactNode }) {
  return <div className="if-page-in">{children}</div>;
}
