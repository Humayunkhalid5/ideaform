/** Re-mounts on navigation between app pages: each page enters with the shared transition. */
export default function AppTemplate({ children }: { children: React.ReactNode }) {
  return <div className="if-page-in">{children}</div>;
}
