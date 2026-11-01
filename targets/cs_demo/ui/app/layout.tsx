import type React from "react";
import type { Metadata } from "next";
import { Inter, Fira_Sans, Fira_Code } from "next/font/google";
import "./globals.css";
import "./bylaw.css";

const inter = Inter({ subsets: ["latin"] });
// Bylaw's own faces, used only inside Bylaw's elements (web/src/styles.css, UI7)
const fira = Fira_Sans({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--bylaw-sans" });
const firaCode = Fira_Code({ subsets: ["latin"], weight: ["400", "500"], variable: "--bylaw-code" });

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
    <html lang="en" className={`${fira.variable} ${firaCode.variable}`}>
      <body className={inter.className}>{children}</body>
    </html>
  );
}
