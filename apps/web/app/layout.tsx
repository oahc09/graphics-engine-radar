import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Graphics Engine Radar",
  description:
    "持续监控图形引擎、Graphics API、GPU、渲染技术和工具链。AI 帮你过滤噪声,只留下真正值得关注的变化。",
};

const NAV = [
  { href: "/", label: "精选" },
  { href: "/events", label: "全部动态" },
  { href: "/trends", label: "趋势" },
  { href: "/topics", label: "主题" },
  { href: "/objects", label: "对象" },
  { href: "/digest", label: "日报" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <header className="site-head">
          <div className="container head-inner">
            <Link href="/" className="brand">
              Graphics Engine <b>Radar</b>
            </Link>
            <nav>
              {NAV.map((n) => (
                <Link key={n.href} href={n.href}>
                  {n.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="container">{children}</main>
        <footer className="site-foot">
          <div className="container">
            Don&apos;t rank news. Detect meaningful changes in graphics technology.
          </div>
        </footer>
      </body>
    </html>
  );
}
