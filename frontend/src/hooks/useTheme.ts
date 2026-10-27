import { useEffect, useState } from "react";
export function useTheme() {
  const [dark, setDark] = useState(() => {
    try {
      return localStorage.getItem("sheetsense-theme") === "dark";
    } catch {
      return false;
    }
  });
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try {
      localStorage.setItem("sheetsense-theme", dark ? "dark" : "light");
    } catch {
      /* Private browsing may disable storage. */
    }
  }, [dark]);
  return { dark, toggle: () => setDark((value) => !value) };
}
