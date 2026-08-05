"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV } from "@/lib/data";

export default function Nav() {
  const path = usePathname();
  return (
    <nav className="mainnav">
      {NAV.map(({ href, label }) => {
        const active =
          href === "/" ? path === "/" : path.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
