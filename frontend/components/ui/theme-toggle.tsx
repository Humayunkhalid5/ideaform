"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

const STORAGE_KEY = "ideaform-theme";

export function ThemeToggle({ className }: { className?: string }) {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next ? "dark" : "light");
    } catch {
      /* private mode: the theme just will not persist */
    }
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
      title={dark ? "Light theme" : "Dark theme"}
      className={cn(
        "grid size-9 place-items-center rounded-lg border border-line bg-surface text-muted transition-colors hover:bg-surface-soft hover:text-ink",
        className,
      )}
    >
      {dark ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </button>
  );
}

/**
 * Applies the saved theme before first paint; pair with suppressHydrationWarning on <html>.
 * Light is the default — dark only applies when the user explicitly toggled it, because
 * the product design is light-first and OS dark mode should not silently flip the app.
 */
export const themeScript = `(function(){try{if(localStorage.getItem("${STORAGE_KEY}")==="dark")document.documentElement.classList.add("dark");}catch(e){}})();`;
