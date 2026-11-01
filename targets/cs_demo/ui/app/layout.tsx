import type React from "react";
import type { Metadata } from "next";
import "./globals.css";
import "./bylaw.css";

// Fonts load at run time, as web/ does, so `next build` needs no network (the gate is offline).
// Inter is the demo's face; Fira Sans and Fira Code are Bylaw's (web/src/styles.css, UI7).
const FONTS =
  "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Sans:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap";

export const metadata: Metadata = {
  title: "Airlines Agent Orchestration · guarded by Bylaw",
  description: "OpenAI's airline customer-service agents demo, with Bylaw checking every tool call",
  icons: {
    icon: "/openai_logo.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        {/* eslint-disable-next-line @next/next/no-page-custom-font */}
        <link rel="stylesheet" href={FONTS} />
      </head>
      <body>{children}</body>
    </html>
  );
}
