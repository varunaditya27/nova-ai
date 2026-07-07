import type { Metadata } from "next";
// Self-hosted variable fonts — bundled in node_modules, so the build never reaches a font CDN.
import "@fontsource-variable/fraunces";
import "@fontsource-variable/instrument-sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";
import { ThemeProvider, themeNoFlashScript } from "@/components/ThemeProvider";

export const metadata: Metadata = {
  title: "Nova",
  description: "Intelligence that remembers.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${GeistMono.variable} h-full`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeNoFlashScript }} />
      </head>
      <body className="relative min-h-full">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
