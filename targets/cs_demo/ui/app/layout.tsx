import type React from "react";
import type { Metadata } from "next";
// Self-hosted fonts (@fontsource, SIL OFL 1.1): no third-party request, and `next build` needs no network.
// Inter is the demo's face; Fira Sans and Fira Code are Bylaw's (web/src/styles.css, UI7).
import "@fontsource/inter/latin-300.css";
import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-500.css";
import "@fontsource/inter/latin-600.css";
import "@fontsource/inter/latin-700.css";
import "@fontsource/fira-sans/latin-400.css";
import "@fontsource/fira-sans/latin-500.css";
import "@fontsource/fira-sans/latin-600.css";
import "@fontsource/fira-sans/latin-700.css";
import "@fontsource/fira-code/latin-400.css";
import "@fontsource/fira-code/latin-500.css";
import "./globals.css";
import "./bylaw.css";

export const metadata: Metadata = {
  title: "Airlines Agent Orchestration · guarded by bylaw",
  description: "OpenAI's airline customer-service agents demo, with bylaw checking every tool call",
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
      <body>{children}</body>
    </html>
  );
}
